from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core import mail
from django.db import IntegrityError
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from unittest.mock import patch

from .email_service import send_approved_outreach
from .models import (
    Company,
    Contact,
    JobPosting,
    OutreachEmail,
    Prospect,
    ProspectEvent,
    SearchIndustry,
    SearchLocation,
    SearchProfile,
    SearchRole,
    SearchSignal,
)
from .services import approve_outreach
from .discovery.providers import (
    GreenhouseBoard,
    GreenhouseJobBoardProvider,
    PublicWebSearchProvider,
    TheMuseSearchProvider,
    greenhouse_boards_from_json,
)
from .discovery.query_builder import build_search_queries
from .discovery.schemas import DiscoveredJob
from .discovery.services import ingest_discovered_job, parse_job_details
from .discovery.source_detection import detect_job_source
from .tasks import discover_jobs_task


class HealthCheckTests(TestCase):
    def test_health_endpoint_reports_the_prospecting_app_is_available(self):
        response = self.client.get(reverse("prospecting:health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"app": "prospecting", "status": "ok"})


class ProspectingModelTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Example Research", domain="example.org")
        self.job = JobPosting.objects.create(
            company=self.company,
            title="Biostatistician",
            source="example-careers",
            source_url="https://example.org/careers/biostatistician",
            source_job_id="bio-001",
        )

    def test_job_source_id_is_unique_per_source(self):
        with self.assertRaises(IntegrityError):
            JobPosting.objects.create(
                company=self.company,
                title="Biostatistician",
                source="example-careers",
                source_url="https://example.org/careers/duplicate",
                source_job_id="bio-001",
            )

    def test_prospect_score_is_limited_to_100(self):
        prospect = Prospect(company=self.company, job_posting=self.job, fit_score=101)

        with self.assertRaises(ValidationError):
            prospect.full_clean()


class ProspectingApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="reviewer", password="test-password", is_staff=True
        )
        self.company = Company.objects.create(name="Example Research", domain="example.org")
        self.job = JobPosting.objects.create(
            company=self.company,
            title="Clinical Data Analyst",
            source="example-careers",
            source_url="https://example.org/careers/clinical-data-analyst",
            source_job_id="clinical-001",
        )
        self.client.force_login(self.user)

    def test_prospect_endpoints_require_authentication(self):
        self.client.logout()

        response = self.client.get(reverse("prospecting:prospect-list"))

        self.assertEqual(response.status_code, 403)

    def test_prospect_requires_job_posting_from_its_company(self):
        other_company = Company.objects.create(name="Other Company", domain="other.example")

        response = self.client.post(
            reverse("prospecting:prospect-list"),
            {"company": other_company.id, "job_posting": self.job.id, "fit_score": 82},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("job_posting", response.json())

    def test_approval_flow_records_activity(self):
        prospect_response = self.client.post(
            reverse("prospecting:prospect-list"),
            {"company": self.company.id, "job_posting": self.job.id, "fit_score": 82},
            content_type="application/json",
        )
        self.assertEqual(prospect_response.status_code, 201)
        prospect_id = prospect_response.json()["id"]

        outreach_response = self.client.post(
            reverse("prospecting:outreach-list"),
            {"prospect": prospect_id, "subject": "A Qantly demo", "body": "Hello from Qantly."},
            content_type="application/json",
        )
        self.assertEqual(outreach_response.status_code, 201)
        outreach_id = outreach_response.json()["id"]

        submit_response = self.client.post(
            reverse("prospecting:outreach-submit-for-approval", args=[outreach_id]),
            content_type="application/json",
        )
        self.assertEqual(submit_response.status_code, 200)
        self.assertEqual(submit_response.json()["status"], "awaiting_approval")

        approve_response = self.client.post(
            reverse("prospecting:outreach-approve", args=[outreach_id]),
            content_type="application/json",
        )
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(approve_response.json()["status"], "approved")
        self.assertEqual(approve_response.json()["approved_by"], self.user.id)

        activity_types = list(Prospect.objects.get(pk=prospect_id).events.values_list("event_type", flat=True))
        self.assertIn("outreach_drafted", activity_types)
        self.assertIn("outreach_approved", activity_types)
        self.assertTrue(ProspectEvent.objects.filter(prospect_id=prospect_id).exists())

    def test_non_staff_user_cannot_approve_outreach(self):
        prospect = Prospect.objects.create(company=self.company, job_posting=self.job, fit_score=82)
        outreach = OutreachEmail.objects.create(
            prospect=prospect,
            subject="A Qantly demo",
            body="Hello from Qantly.",
            status=OutreachEmail.Status.AWAITING_APPROVAL,
        )
        non_staff = get_user_model().objects.create_user(username="member", password="test-password")
        self.client.force_login(non_staff)

        response = self.client.post(reverse("prospecting:outreach-approve", args=[outreach.id]))

        self.assertEqual(response.status_code, 403)


class OutreachDeliveryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="reviewer", is_staff=True)
        self.company = Company.objects.create(name="Example Research", domain="example.org")
        self.job = JobPosting.objects.create(
            company=self.company,
            title="Biostatistician",
            source="example-careers",
            source_url="https://example.org/careers/biostatistician",
        )
        self.prospect = Prospect.objects.create(company=self.company, job_posting=self.job, fit_score=88)
        self.contact = Contact.objects.create(
            company=self.company,
            name="A Reviewer",
            email="reviewer@example.org",
        )

    def test_unapproved_outreach_cannot_be_sent(self):
        outreach = OutreachEmail.objects.create(
            prospect=self.prospect,
            contact=self.contact,
            subject="A Qantly demo",
            body="Hello from Qantly.",
        )

        with self.assertRaises(ValidationError):
            send_approved_outreach(outreach)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_approved_outreach_is_sent_and_audited(self):
        outreach = OutreachEmail.objects.create(
            prospect=self.prospect,
            contact=self.contact,
            subject="A Qantly demo",
            body="Hello from Qantly.",
            status=OutreachEmail.Status.AWAITING_APPROVAL,
        )
        approve_outreach(outreach, self.user)

        send_approved_outreach(outreach)
        outreach.refresh_from_db()

        self.assertEqual(outreach.status, OutreachEmail.Status.SENT)
        self.assertEqual(outreach.reply_status, OutreachEmail.ReplyStatus.PENDING)
        self.assertEqual(len(mail.outbox), 1)


class JobDiscoveryTests(TestCase):
    def setUp(self):
        self.profile = SearchProfile.objects.create(name="Healthcare Analytics")
        SearchSignal.objects.create(
            search_profile=self.profile,
            value="SAS",
            category=SearchSignal.Category.SOFTWARE,
        )
        SearchSignal.objects.create(
            search_profile=self.profile,
            value="Kaplan-Meier",
            category=SearchSignal.Category.METHOD,
        )

    def test_parser_extracts_clean_text_and_profile_matched_signals(self):
        parsed = parse_job_details(
            "<p>Senior Clinical Data Analyst with SAS, Python, and Kaplan-Meier experience.</p>", self.profile
        )

        self.assertEqual(parsed.description, "Senior Clinical Data Analyst with SAS, Python, and Kaplan-Meier experience.")
        self.assertEqual(parsed.requirements, ["SAS"])
        self.assertIn("Kaplan-Meier", parsed.matched_signals)
        self.assertEqual(parsed.seniority, "Senior")
        self.assertEqual(parsed.department, "")

    def test_ingestion_is_idempotent_for_a_source_job_id(self):
        discovered_job = DiscoveredJob(
            source="greenhouse",
            source_url="https://boards.greenhouse.io/example/jobs/101",
            source_job_id="101",
            company_name="Example Research",
            company_domain="example.org",
            title="Biostatistician",
            raw_content="Clinical trial experience with R and survival analysis.",
        )

        job, created = ingest_discovered_job(discovered_job, self.profile)
        same_job, created_again = ingest_discovered_job(discovered_job, self.profile)

        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(job.id, same_job.id)
        self.assertEqual(JobPosting.objects.count(), 1)
        self.assertEqual(same_job.status, JobPosting.Status.PARSED)
        self.assertEqual(same_job.search_profile, self.profile)

    def test_ingestion_filters_a_mirrored_job_with_a_different_source(self):
        original = DiscoveredJob(
            source="greenhouse",
            source_url="https://boards.greenhouse.io/example/jobs/101",
            source_job_id="101",
            company_name="Example Research",
            company_domain="example.org",
            title="Biostatistician",
            location="Remote",
            raw_content="Clinical trial experience with R and survival analysis.",
        )
        mirrored = original.model_copy(
            update={
                "source": "public-search",
                "source_url": "https://example.org/jobs/biostatistician",
                "source_job_id": "mirrored-101",
            }
        )
        original_job, _ = ingest_discovered_job(original, self.profile)

        duplicate, created = ingest_discovered_job(mirrored, self.profile)

        self.assertFalse(created)
        self.assertEqual(duplicate.id, original_job.id)
        self.assertEqual(JobPosting.objects.count(), 1)


class SearchProfileTests(TestCase):
    def setUp(self):
        self.profile = SearchProfile.objects.create(
            name="Configurable Analytics", description="Database-driven discovery", freshness_days=7
        )
        self.role = SearchRole.objects.create(search_profile=self.profile, name="Data Analyst", weight=10)
        self.signal = SearchSignal.objects.create(
            search_profile=self.profile,
            value="Python",
            category=SearchSignal.Category.SOFTWARE,
            weight=8,
        )
        self.location = SearchLocation.objects.create(search_profile=self.profile, country="Canada")
        self.industry = SearchIndustry.objects.create(search_profile=self.profile, name="Research")

    def test_query_generation_reads_database_configuration(self):
        queries = build_search_queries(self.profile)

        self.assertEqual(queries, ['role:"Data Analyst" signal:"Python" Research location:"Canada" jobs past 7 days'])

    def test_initial_qantly_profile_is_seeded_by_migration(self):
        seeded_profile = SearchProfile.objects.get(name="Qantly Healthcare & Statistical Analytics")

        self.assertTrue(seeded_profile.roles.filter(name="Biostatistician", is_active=True).exists())
        self.assertTrue(seeded_profile.roles.filter(name="Analytics Engineer", is_active=True).exists())
        self.assertTrue(seeded_profile.signals.filter(value="SAS", is_active=True).exists())
        self.assertTrue(seeded_profile.locations.filter(country="USA", is_active=True).exists())

    def test_inactive_configuration_is_excluded_from_queries(self):
        self.role.is_active = False
        self.role.save(update_fields=["is_active"])

        self.assertEqual(build_search_queries(self.profile), [])

    def test_search_profile_api_activation_requires_staff(self):
        user = get_user_model().objects.create_user(username="member", password="test-password")
        self.client.force_login(user)
        response = self.client.post(reverse("prospecting:search-profile-deactivate", args=[self.profile.id]))

        self.assertEqual(response.status_code, 403)


class DiscoveryProviderTests(TestCase):
    def test_optional_greenhouse_configuration_is_empty_safe(self):
        self.assertEqual(greenhouse_boards_from_json("[]"), [])
        self.assertEqual(GreenhouseJobBoardProvider([]).fetch_jobs(), [])

    def test_unconfigured_public_web_provider_returns_no_fabricated_jobs(self):
        provider = PublicWebSearchProvider(provider_name="", api_key="")

        self.assertFalse(provider.is_configured)
        self.assertEqual(provider.search_jobs('"Data Analyst" jobs'), [])

    def test_discovery_task_runs_when_greenhouse_is_not_configured(self):
        with patch.dict("os.environ", {"SEARCH_PROVIDER": "", "SEARCH_API_KEY": ""}):
            result = discover_jobs_task.run()

        self.assertEqual(result["greenhouse_boards"], 0)
        self.assertFalse(result["public_web_configured"])

    def test_source_detection(self):
        self.assertEqual(detect_job_source("https://boards.greenhouse.io/acme/jobs/1"), "greenhouse")
        self.assertEqual(detect_job_source("https://job-boards.greenhouse.io/acme/jobs/1"), "greenhouse")
        self.assertEqual(detect_job_source("https://jobs.lever.co/acme/1"), "lever")
        self.assertEqual(detect_job_source("https://jobs.ashbyhq.com/acme/1"), "ashby")
        self.assertEqual(detect_job_source("https://www.themuse.com/jobs/acme/1"), "themuse")
        self.assertEqual(detect_job_source("https://careers.example.org/jobs/1"), "generic")

    def test_greenhouse_provider_normalizes_to_discovered_job(self):
        provider = GreenhouseJobBoardProvider([])
        board = GreenhouseBoard(company_name="Example Research", board_token="example", company_domain="example.org")

        job = provider.normalize_job(
            board,
            {
                "id": 101,
                "title": "Biostatistician",
                "absolute_url": "https://boards.greenhouse.io/example/jobs/101",
                "location": {"name": "Remote"},
                "content": "Clinical analysis",
            },
        )

        self.assertEqual(job.source, "greenhouse")
        self.assertEqual(job.source_job_id, "101")
        self.assertEqual(job.company_name, "Example Research")

    def test_the_muse_provider_normalizes_and_matches_public_jobs(self):
        provider = TheMuseSearchProvider(max_pages=1)
        job = provider.normalize_job(
            {
                "id": 202,
                "name": "Clinical Data Analyst",
                "contents": "Clinical research and SAS experience.",
                "publication_date": "2026-08-31T00:00:00Z",
                "company": {"name": "Example Clinical"},
                "locations": [{"name": "Remote"}],
                "refs": {"landing_page": "https://www.themuse.com/jobs/example/clinical-data-analyst"},
            }
        )

        self.assertEqual(job.source, "themuse")
        self.assertEqual(job.company_name, "Example Clinical")
        self.assertTrue(
            provider._matches_query(job, ["clinical data analyst", "sas"], ["remote"], freshness_days=None)
        )

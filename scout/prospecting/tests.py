from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core import mail
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from .email_service import send_approved_outreach
from .models import Company, Contact, JobPosting, Outreach, Prospect
from .services import approve_outreach
from .discovery.schemas import DiscoveredJob
from .discovery.services import ingest_discovered_job, parse_job_details


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
        with self.assertRaises(Exception):
            JobPosting.objects.create(
                company=self.company,
                title="Biostatistician",
                source="example-careers",
                source_url="https://example.org/careers/duplicate",
                source_job_id="bio-001",
            )

    def test_prospect_score_is_limited_to_100(self):
        prospect = Prospect(company=self.company, job_posting=self.job, fit_score=101)

        with self.assertRaises(Exception):
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

        activity_types = list(Prospect.objects.get(pk=prospect_id).activities.values_list("event_type", flat=True))
        self.assertIn("outreach_drafted", activity_types)
        self.assertIn("outreach_approved", activity_types)

    def test_non_staff_user_cannot_approve_outreach(self):
        prospect = Prospect.objects.create(company=self.company, job_posting=self.job, fit_score=82)
        outreach = Outreach.objects.create(
            prospect=prospect,
            subject="A Qantly demo",
            body="Hello from Qantly.",
            status=Outreach.Status.AWAITING_APPROVAL,
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
        outreach = Outreach.objects.create(
            prospect=self.prospect,
            contact=self.contact,
            subject="A Qantly demo",
            body="Hello from Qantly.",
        )

        with self.assertRaises(ValidationError):
            send_approved_outreach(outreach)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_approved_outreach_is_sent_and_audited(self):
        outreach = Outreach.objects.create(
            prospect=self.prospect,
            contact=self.contact,
            subject="A Qantly demo",
            body="Hello from Qantly.",
            status=Outreach.Status.AWAITING_APPROVAL,
        )
        approve_outreach(outreach, self.user)

        send_approved_outreach(outreach)
        outreach.refresh_from_db()

        self.assertEqual(outreach.status, Outreach.Status.SENT)
        self.assertEqual(outreach.reply_status, Outreach.ReplyStatus.PENDING)
        self.assertEqual(len(mail.outbox), 1)


class JobDiscoveryTests(TestCase):
    def test_parser_extracts_clean_text_and_analytics_signals(self):
        parsed = parse_job_details(
            "<p>Senior Clinical Data Analyst with SAS, Python, and Kaplan-Meier experience.</p>"
        )

        self.assertEqual(parsed.description, "Senior Clinical Data Analyst with SAS, Python, and Kaplan-Meier experience.")
        self.assertEqual(parsed.requirements, ["SAS", "Python"])
        self.assertIn("Kaplan-Meier", parsed.analytics_signals)
        self.assertEqual(parsed.seniority, "Senior")
        self.assertEqual(parsed.department, "Clinical")

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

        job, created = ingest_discovered_job(discovered_job)
        same_job, created_again = ingest_discovered_job(discovered_job)

        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(job.id, same_job.id)
        self.assertEqual(JobPosting.objects.count(), 1)
        self.assertEqual(same_job.status, JobPosting.Status.PARSED)
        self.assertIn("survival analysis", same_job.analytics_signals)

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
        original_job, _ = ingest_discovered_job(original)

        duplicate, created = ingest_discovered_job(mirrored)

        self.assertFalse(created)
        self.assertEqual(duplicate.id, original_job.id)
        self.assertEqual(JobPosting.objects.count(), 1)

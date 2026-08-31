from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Company, JobPosting, Prospect


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
        self.user = get_user_model().objects.create_user(username="reviewer", password="test-password")
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

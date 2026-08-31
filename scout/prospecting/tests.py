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

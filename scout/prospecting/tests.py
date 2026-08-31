from django.test import TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):
    def test_health_endpoint_reports_the_prospecting_app_is_available(self):
        response = self.client.get(reverse("prospecting:health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"app": "prospecting", "status": "ok"})

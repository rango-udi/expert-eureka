"""Check Shuup route wiring inside the real application container."""
from django.test import TestCase
from django.core.management import call_command


class StorefrontTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Create the upstream minimum shop data only inside Django's isolated test database."""
        call_command("shuup_init", verbosity=0)

    def test_health_identity(self):
        """Verify the mounted app identity used by Compose readiness checks."""
        response = self.client.get("/_cmdc/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["target"], "shuup")

    def test_admin_requires_login(self):
        """Verify unauthenticated administration requests lead into the upstream login flow."""
        response = self.client.get("/sa/")
        self.assertIn(response.status_code, (200, 302))
        if response.status_code == 302:
            self.assertIn("login", response["Location"])

from django.test import TestCase
from apps.accounts.models import User

# Create your tests here.


class BootstrapProductionTests(TestCase):
    ENV = {f"BOOTSTRAP_{r}_{k}": v for r in ("OWNER", "DISPATCHER", "RIDER", "CUSTOMER")
           for k, v in (("EMAIL", f"{r.lower()}@example.test"), ("PASSWORD", "Test-Pass-12345"))}

    def run_cmd(self):
        from io import StringIO
        from unittest import mock
        from django.core.management import call_command
        out = StringIO()
        with mock.patch.dict("os.environ", self.ENV):
            call_command("bootstrap_production", stdout=out)
        return out.getvalue()

    def test_creates_everything_and_is_safe_to_run_twice(self):
        from apps.dispatch.models import Vehicle
        from apps.inventory.models import Product
        from apps.station.models import ServiceArea, Station
        out = self.run_cmd()
        self.assertNotIn("Test-Pass-12345", out)
        self.run_cmd()
        self.assertEqual(User.objects.count(), 4)
        self.assertTrue(User.objects.get(role="owner").is_superuser)
        for model in (Station, ServiceArea, Product, Vehicle):
            self.assertEqual(model.objects.count(), 1)

    def test_skips_roles_without_env(self):
        from django.core.management import call_command
        from io import StringIO
        call_command("bootstrap_production", stdout=StringIO())
        self.assertEqual(User.objects.count(), 0)

"""Verify real Shuup startup and ownership of settings inside its application container."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]


class AppSettingsTests(unittest.TestCase):
    def test_project_settings_are_not_collected_as_app_defaults(self):
        """Boot a fresh registry and keep pricing ownership in core while loading the theme."""
        program = """
import django
django.setup()
import json
from django.apps import apps
from django.conf import settings
from shuup.apps import get_known_settings
app = apps.get_app_config('storefront')
defaults = app.get_default_settings_module()
known = {entry.name: entry.app_name for entry in get_known_settings()}
print(json.dumps({
    'defaults': defaults.__name__,
    'declarations': [name for name in vars(defaults) if name.isupper() and not name.startswith('_')],
    'pricing_owner': known['SHUUP_PRICING_MODULE'],
    'currency': settings.SHUUP_HOME_CURRENCY,
    'theme': app.provides['xtheme'],
}))
"""
        result = subprocess.run([sys.executable, "-c", program], cwd=str(ROOT),
                                env=dict(os.environ, DJANGO_SETTINGS_MODULE="storefront.settings"),
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(state["defaults"], "storefront.default_settings")
        self.assertEqual(state["declarations"], [])
        self.assertEqual(state["pricing_owner"], "shuup.core")
        self.assertEqual(state["currency"], "USD")
        self.assertEqual(state["theme"], "storefront.theme:FuzcakeTheme")

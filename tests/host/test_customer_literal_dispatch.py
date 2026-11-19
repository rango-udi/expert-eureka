"""Check exact typed fixture values with recorded keywords, without browser execution."""
import ast
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


class LiteralDispatchTests(unittest.TestCase):
    """Prevent runtime data generation from diverging from the readable test cases."""

    def methods(self):
        """Compile only literal form-fill helpers into an isolated namespace."""
        tree = ast.parse((ROOT / 'apps/shuup/tests/robot/CustomerJourney.py').read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in ('_fill_registration','_login')]
        namespace = {'os': os}
        for method in methods:
            module = ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[]))
            exec(compile(module, '<literal-form-dispatch>', 'exec'), namespace)
        return namespace

    def test_registration_uses_both_exact_declared_passwords(self):
        """Blank and mismatched values must reach the actual form, never a generated substitute."""
        calls = []
        def record(name, *arguments):
            """Record a browser keyword call without launching a page."""
            calls.append((name, *arguments))
        def secret(selector, key):
            """Observe the already materialized password value before browser entry."""
            calls.append(('secret', selector, os.environ[key]))
        spy = SimpleNamespace(_kw=record, _secret=secret)
        inputs = {'username':'lucas.parker','email':'lucas.parker@fuzcake.test','password1':'Lucas!7362Maple','password2':''}
        with patch.dict(os.environ):
            self.methods()['_fill_registration'](spy, inputs)
        self.assertIn(('secret', 'css=input[name="password1"]', 'Lucas!7362Maple'), calls)
        self.assertIn(('secret', 'css=input[name="password2"]', ''), calls)
        self.assertIn(('Fill Text', 'css=input[name="username"]', 'lucas.parker'), calls)

    def test_login_uses_literal_wrong_password(self):
        """A wrong-password case must type the password visible in the reviewed manual case."""
        observed = []
        def record(*args):
            """Record form actions without calling Robot or Browser."""
            observed.append(args)
        def secret(selector, key):
            """Read the exact test value assigned by the login helper."""
            observed.append((selector, os.environ[key]))
        spy = SimpleNamespace(_kw=record, _secret=secret)
        with patch.dict(os.environ):
            self.methods()['_login'](spy, 'oliver.bennett', 'Oliver!0000Maple')
        self.assertTrue(any(row[-1] == 'Oliver!0000Maple' for row in observed))

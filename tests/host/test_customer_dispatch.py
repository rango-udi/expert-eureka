"""Check customer CLI argument boundaries with recorded children, not app execution.

Only the dispatcher function's AST is compiled. Django, Browser, the generator
and Robot are never imported or launched; subprocess calls are replaced by a
recorder. This is host orchestration evidence, not functional UI evidence.
"""
import ast
import os
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CustomerDispatchTests(unittest.TestCase):
    """Protect suite selection and reject filters that DataDriver cannot honor."""

    def setUp(self):
        """Isolate the source dispatch function and provide synthetic configuration."""
        tree = ast.parse((ROOT / 'apps/shuup/scripts/commands.py').read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'robot')
        module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
        self.calls = []
        values = {role + '_' + field: 'synthetic-value' for role in ('ADMIN', 'CUSTOMER', 'STAFF')
                  for field in ('EMAIL', 'PASSWORD')}
        values['COUPON_CODE'] = 'FUZCAKE10'
        namespace = {'os': os, 'ROOT': Path('/app'), 'PYTHON': Path('/python'), 'Path': Path,
                     'load': lambda: values, 'run': self.record}
        exec(compile(module, '<isolated-customer-dispatch>', 'exec'), namespace)
        self.dispatch = namespace['robot']

    def record(self, arguments, **options):
        """Capture arguments without executing any child or exposing credential values."""
        self.calls.append(([str(value) for value in arguments], options))

    def test_customer_filter_is_applied_before_robot_not_forwarded_as_robot_selection(self):
        """DataDriver receives filtered CSV while Robot receives only executable options."""
        self.dispatch(['--customer', '--customer-case', 'SH-CUST-Q*', '--customer-stage', 'quantity', '--dryrun'])
        self.assertEqual(self.calls[0][0], ['/python', 'scripts/customer_design.py', '--case', 'SH-CUST-Q*', '--stage', 'quantity'])
        robot = self.calls[1][0]
        self.assertEqual(robot[-1], '/app/reports/customer/run.robot')
        self.assertIn('--exitonerror', robot)
        self.assertIn('--dryrun', robot)
        self.assertNotIn('--customer', robot)
        self.assertNotIn('--customer-case', robot)

    def test_standard_selection_is_rejected_before_any_child_is_launched(self):
        """A known-invalid DataDriver filter cannot silently run zero tests or a wrong subset."""
        for option in ('--test', '--include', '--exclude', '--rerunfailed'):
            with self.subTest(option=option), self.assertRaises(ValueError):
                self.dispatch(['--customer', option, 'anything'])
        self.assertEqual(self.calls, [])

    def test_customer_selection_requires_its_mode_and_value(self):
        """Missing mode or filter value fails clearly before generation or execution."""
        for arguments in (['--customer-case', 'SH-CUST-Q*'], ['--customer', '--customer-case']):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                self.dispatch(arguments)
        self.assertEqual(self.calls, [])

    def test_wallet_and_customer_modes_cannot_replace_each_others_suite(self):
        """Selecting two unrelated models must fail instead of quietly choosing the last."""
        with self.assertRaises(ValueError):
            self.dispatch(['--customer', '--design'])
        self.assertEqual(self.calls, [])

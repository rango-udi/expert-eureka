"""Verify finite customer coverage and model rejection in the tools container."""
import copy
import json
from pathlib import Path
import unittest
from scripts.customer_design import build_plan, read_reference
from test_design.specification import load_specification


class CustomerDesignTests(unittest.TestCase):
    """Protect traceability and genuine coverage reduction, not browser outcomes."""

    def setUp(self):
        """Load source specifications without touching a Django database."""
        self.model = load_specification('tests/data/CUSTOMER_DESIGN.yaml')
        self.catalogue = read_reference('catalogue')
        self.store = read_reference('store')
        self.partners = read_reference('partners')

    def plan(self, model=None):
        """Build the plan from independent read-only reference documents."""
        return build_plan(model or self.model, self.catalogue, self.store, self.partners)

    def test_default_plan_covers_all_declared_stages_with_52_executions(self):
        """The default has nine quantity, eight registration, four login and one E2E case."""
        plan = self.plan()
        counts = {stage: sum(case['stage'] == stage for case in plan['cases'])
                  for stage in ('quantity', 'registration', 'login', 'e2e')}
        self.assertEqual(counts, {'quantity': 9, 'registration': 8, 'login': 4, 'e2e': 1})
        self.assertEqual(plan['selected_count'], 52)
        self.assertEqual(plan['execution_status'], 'not_executed')
        self.assertEqual(plan['numeric_plan']['excluded_obligations'], [])

    def test_every_selected_execution_has_a_real_exclusive_obligation(self):
        """Removing any selected candidate loses modeled coverage; no synthetic witness IDs."""
        plan = self.plan()
        all_coverage = set(plan['planned_obligations'])
        self.assertTrue(plan['minimum_proven_within_declared_candidates'])
        for case in plan['cases']:
            remaining = {item for other in plan['cases'] if other['id'] != case['id'] for item in other['covers']}
            self.assertTrue(all_coverage - remaining, case['id'])
        self.assertFalse(any(item.startswith('WITNESS-') for item in all_coverage))

    def test_quantities_include_both_robust_outside_values_and_fraction(self):
        """BVA and EP overlap in one execution rather than duplicating shared representatives."""
        rows = {row['value']: row for row in self.plan()['cases'] if row['stage'] == 'quantity'}
        self.assertEqual(set(rows), {'0', '1', '2', '3', '24', '25', '26', '', '1.5'})
        self.assertTrue({'bva:quantity:below', 'ep:quantity:below'} <= set(rows['0']['covers']))
        self.assertTrue({'bva:quantity:above', 'ep:quantity:above_stock'} <= set(rows['26']['covers']))
        self.assertEqual(rows['1.5']['expected'], 'rejected')

    def test_stock_and_order_skus_cannot_silently_change_the_boundary_oracle(self):
        """Boundary data stays independent of the products consumed by the E2E order."""
        model = copy.deepcopy(self.model)
        model['order_products'][0] = model['quantity_product']
        with self.assertRaises(ValueError):
            self.plan(model)
        model = copy.deepcopy(self.model)
        model['quantity_model']['fields']['quantity']['max'] = '26'
        with self.assertRaises(ValueError):
            self.plan(model)

    def test_reference_ids_and_negative_case_ids_are_checked(self):
        """Typos and duplicate IDs fail generation before any browser account is created."""
        model = copy.deepcopy(self.model)
        model['shipping_address'] = 'missing-address'
        with self.assertRaises(ValueError):
            self.plan(model)
        model = copy.deepcopy(self.model)
        model['negative_cases'].append(model['negative_cases'][0])
        with self.assertRaises(ValueError):
            self.plan(model)

    def test_export_has_in_suite_template_and_filters_before_datadriver(self):
        """Dynamic tests must retain a local argument wrapper and preselect exact source rows."""
        import csv
        import tempfile
        from scripts.customer_design import export

        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            plan = export('tests/data/CUSTOMER_DESIGN.yaml', output, ['SH-CUST-R0[13]'])
            self.assertEqual(plan['scheduled_ids'], ['SH-CUST-R01', 'SH-CUST-R03'])
            self.assertEqual(plan['selected_count'], 52)
            self.assertEqual(plan['scheduled_count'], 2)
            with (output / 'robot_transport.csv').open() as stream:
                rows = list(csv.reader(stream, delimiter=';'))
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0][1], '${payload}')
            suite = (output / 'run.robot').read_text()
            self.assertIn('Test Template    Run Customer Case', suite)
            self.assertIn('*** Keywords ***\nRun Customer Case\n    [Arguments]    ${payload}', suite)
            self.assertIn('Execute Customer Case    ${payload}', suite)
            with self.assertRaises(ValueError):
                export('tests/data/CUSTOMER_DESIGN.yaml', output, ['SH-CUST-MISSING'])

    def test_unbound_decision_rules_cannot_claim_coverage(self):
        """New metadata rules need executable checkpoints before receiving coverage credit."""
        model = copy.deepcopy(self.model)
        model['decision_rules'].append({'id': 'D-UNBOUND', 'expected': 'not implemented'})
        with self.assertRaises(ValueError):
            self.plan(model)

    def test_readable_cases_robot_payloads_and_report_have_identical_inputs(self):
        """A single source must reach the readable table, DataDriver and workbook unchanged."""
        import base64
        import csv
        import tempfile
        from scripts.customer_design import export
        from scripts.customer_report_data import prepare_report
        from scripts.customer_case_contract import case_records
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            plan = export('tests/data/CUSTOMER_DESIGN.yaml', output)
            with (output / 'robot_transport.csv').open() as stream:
                payloads = [json.loads(base64.b64decode(row['${payload}']))
                            for row in csv.DictReader(stream, delimiter=';')]
            with (output / 'test_cases.csv').open(encoding='utf-8-sig') as stream:
                readable = list(csv.reader(stream))
            report = prepare_report()
            self.assertEqual(len(readable), 72)
            english = report['_english_report']
            self.assertEqual(readable[0], english['headers'])
            self.assertEqual([row[0] for row in readable[1:]], [r['id'] for r in english['cases']])
            self.assertEqual([row[6] for row in readable[1:]], [r['input'] for r in english['cases']])
            self.assertEqual([row[7] for row in readable[1:]], [r['expected'] for r in english['cases']])
            self.assertEqual(payloads, plan['cases'])
            snapshot = json.loads((output / 'model.json').read_text())
            from test_design.specification import semantic_hash
            self.assertEqual(snapshot['_provenance']['case_sha256'], {row['id']: semantic_hash(row) for row in payloads})
            self.assertEqual(report['model_sha256'], plan['model_sha256'])
            login = next(row for row in payloads if row['id'] == 'SH-CUST-L04')['inputs']
            manual = next(row for row in report['cases'] if row['id'] == 'TC-DN-005')
            self.assertIn(login['username'], manual['input'])
            self.assertIn(login['password'], manual['input'])

    def test_unsupported_symbol_and_unquoted_input_fail_before_execution(self):
        """Reject values that cannot be executed exactly as specified."""
        for value in ('$ignored-token', 123):
            model = copy.deepcopy(self.model)
            model['negative_cases'][-1]['value'] = value
            with self.assertRaises(ValueError):
                self.plan(model)


    def test_all_form_values_are_literal_including_public_passwords(self):
        """No runtime randomization or unresolved token can replace reviewed account values."""
        from scripts.customer_report_data import prepare_report
        plan = self.plan()
        rows = {row['id']: row for row in plan['cases']}
        for case in rows.values():
            self.assertNotIn('$', json.dumps(case['inputs']))
        self.assertEqual(rows['SH-CUST-R03']['inputs']['username'], self.model['test_data']['existing_customer']['username'])
        self.assertEqual(rows['SH-CUST-R06']['inputs']['password1'], '')
        self.assertEqual(rows['SH-CUST-R06']['inputs']['password2'], self.model['test_data']['registration_baseline']['password2'])
        report = prepare_report()
        for row in report['cases']:
            text = ' '.join(row[key] for key in ('title','description','preconditions','steps','input','expected'))
            for token in ('${', '$existing', '$empty', '$unknown', 'ROBOT_', 'uuid', '<unique>', 'css=', 'os.environ', 'password1:'):
                self.assertNotIn(token, text, row['id'])
        for row in report['cases']:
            if row['id'].startswith(('TC-DK-', 'TC-DN-', 'TC-GH-')) and row['id'] != 'TC-GH-010':
                self.assertIn('M\u1eadt kh\u1ea9u:', row['input'])

    def test_direct_script_entrypoint_with_only_shared_pythonpath(self):
        """Reproduce Docker's script invocation without adding the application to PYTHONPATH."""
        import os
        import subprocess
        import sys
        import tempfile
        app = Path(__file__).resolve().parents[2]
        environment = dict(os.environ, PYTHONPATH=str(app.parent.parent / 'test-design'))
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, 'scripts/customer_design.py', '--output', folder],
                                    cwd=app, env=environment, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads((Path(folder) / 'coverage.json').read_text())
            self.assertEqual(plan['selected_count'], 52)
            for invocation in ([sys.executable, 'scripts/customer_report.py', '--help'],
                               [sys.executable, '-m', 'scripts.customer_report', '--help']):
                result = subprocess.run(invocation, cwd=app, env=environment, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_scenario_wording_preserves_ids_across_locales(self):
        """Describe the input situation while keeping rejection in the expected-result field."""
        from scripts.customer_report_data import prepare_report
        from scripts.customer_case_contract import case_records
        plan = self.plan()
        manual = prepare_report()['cases']
        records = case_records(self.model, plan['cases'])
        for row in manual:
            for key in ('title','description'):
                text = row[key].casefold()
                for token in ('kh\u00f4ng ', 'n\u00ean ', 'h\u00e3y ', 'c\u1ea7n ', 't\u1eeb ch\u1ed1i'):
                    self.assertNotIn(token, text, row['id'] + ':' + key)
        for case, record in zip(plan['cases'], records):
            self.assertEqual(case['id'], record['id'])
            self.assertEqual(case['title'], record['title'])
            self.assertEqual(case['description'], record['description'])
        rejected = next(row for row in manual if row['id'] == 'TC-DK-002')
        self.assertIn('\u0110\u0103ng k\u00fd v\u1edbi t\u00ean \u0111\u0103ng nh\u1eadp \u0111\u1ec3 tr\u1ed1ng', rejected['title'])
        self.assertIn('kh\u00f4ng', rejected['expected'].casefold())

    def test_report_shared_path_supports_shallow_container_layout(self):
        """The actual /app/scripts path must resolve the shared package without parents[3]."""
        import ast
        source = Path('scripts/customer_report_contract.py').read_text()
        assignments = [node for node in ast.parse(source).body if isinstance(node, ast.Assign)
                       and any(isinstance(target, ast.Name) and target.id in ('APP_ROOT','shared') for target in node.targets)]
        namespace = {'Path': Path, '__file__': '/app/scripts/customer_report_contract.py'}
        for node in assignments:
            module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
            exec(compile(module, '<container-package-root>', 'exec'), namespace)
        self.assertEqual(namespace['shared'], Path('/test-design'))


    def test_non_excel_exports_are_english_and_preserve_literal_values(self):
        """Console names, payloads and readable exports must not inherit Excel localization."""
        import csv
        import tempfile
        from scripts.customer_design import export
        from scripts.customer_report_data import prepare_report
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            plan = export('tests/data/CUSTOMER_DESIGN.yaml', output)
            for name in ('robot_transport.csv','execution_cases.csv','test_cases.csv','report_data.json'):
                self.assertTrue((output / name).read_text(encoding='utf-8').isascii(), name)
            def assert_english(value):
                """Check decoded JSON strings so escaped Vietnamese cannot hide in exports."""
                if isinstance(value, str):
                    self.assertTrue(value.isascii(), value)
                elif isinstance(value, dict):
                    for item in value.values():
                        assert_english(item)
                elif isinstance(value, list):
                    for item in value:
                        assert_english(item)
            markdown = (output / 'test_cases.md').read_text(encoding='utf-8')
            self.assertFalse(markdown.isascii())
            self.assertIn('oliver.bennett', markdown)
            for row in prepare_report()['cases']:
                self.assertIn(row['id'] + ' - ' + row['title'], markdown)
            for name in ('model.json','coverage.json','report_data.json'):
                assert_english(json.loads((output / name).read_text()))
            report = prepare_report()
            localized = {row['id']: row for row in report['cases']}
            english = report['_english_report']['cases']
            for row in english:
                self.assertEqual(row['robot_ids'], localized[row['id']]['robot_ids'])
            for case in plan['cases']:
                self.assertTrue(case['title'].isascii())
                self.assertTrue(case['description'].isascii())
            self.assertIn(self.model['test_data']['journey_customer']['password1'], localized['TC-HT-001']['input'])
            self.assertIn(self.model['test_data']['journey_customer']['password1'], next(row['input'] for row in english if row['id']=='TC-HT-001'))

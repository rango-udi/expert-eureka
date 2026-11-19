"""Verify documentary evidence joining with synthetic inputs; no app execution."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('customer_report_data', ROOT / 'apps/shuup/scripts/customer_report_data.py')
REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT)


class CustomerReportTests(unittest.TestCase):
    """Keep execution, design and nested checkpoints distinct."""

    def test_design_does_not_invent_execution(self):
        """Business scenarios start unrun, regardless of their supporting automation."""
        data = REPORT.prepare_report()
        self.assertEqual((data['case_count'], data['automation_count']), (71, 52))
        self.assertEqual(len(data['headers']), 15)
        self.assertTrue(all(row['reporter'] == '' for row in data['cases']))
        self.assertTrue(all(row['actual'] == data['labels']['not_run'] for row in data['cases']))
        self.assertTrue(all(row['status'] == data['labels']['new'] for row in data['cases']))

    def test_automation_pass_is_only_reference_evidence(self):
        """An old PASS does not certify a newly authored scenario and its example inputs."""
        data = REPORT.prepare_report(results={'tests': {'SH-CUST-E01': {'status': 'PASS'}}},
                                     evidence_path='reports/results.json')
        row = next(item for item in data['cases'] if item['id'] == 'TC-DK-001')
        trace = next(item for item in data['trace'] if item[0] == row['id'])
        self.assertEqual(row['actual'], data['labels']['not_run'])
        self.assertEqual(row['evidence'], '')
        self.assertIn('SH-CUST-E01: PASS', trace[4])
        self.assertEqual(trace[5], 'reports/results.json#SH-CUST-E01')

    def test_automation_failure_does_not_become_a_business_defect(self):
        """A blocked script must not label every related business scenario as failed."""
        data = REPORT.prepare_report(results={'tests': {'SH-CUST-E01': {'status': 'FAIL', 'failure_kind': 'test_selector'}}})
        self.assertTrue(all(row['actual'] == data['labels']['not_run'] for row in data['cases']))
        self.assertTrue(any('SH-CUST-E01: FAIL' in row[4] for row in data['trace']))

    def test_trace_has_no_orphan_design_obligation(self):
        """Every declared class/rule/boundary has a witness and every case reference resolves."""
        data = REPORT.prepare_report()
        obligations = {row[0] for row in data.get('extra_bva', [])} | {row[0] for row in data['bva_rows']} | {row[0] for row in data['ep']}
        obligations |= {rule for table in data['decisions'] for rule in table['rules']}
        covered = {reference.strip() for case in data['cases'] for reference in case['analysis'].split(',')}
        self.assertTrue(obligations <= covered)
        self.assertEqual(len({rid for case in data['cases'] for rid in case['robot_ids']}), 52)
        self.assertEqual(len(data['trace']), len(data['cases']))
        self.assertTrue(all(case['requirement'] in data['requirements'] for case in data['cases']))
        self.assertTrue(any(len(case['analysis'].split(',')) > 1 for case in data['cases']))
        e2e_related = [case for case in data['cases'] if 'SH-CUST-E01' in case['robot_ids']]
        self.assertGreater(len(e2e_related), 1)

    def test_rejects_dtd_and_duplicate_ids(self):
        """Ambiguous or unsafe XML must fail before output is produced."""
        texts = ['<!DOCTYPE robot><robot/>', '<robot><test name="SH-CUST-Q01 A"><status status="PASS"/></test><test name="SH-CUST-Q01 B"><status status="PASS"/></test></robot>']
        for text in texts:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'output.xml'
                path.write_text(text)
                with self.assertRaises(ValueError): REPORT.import_results(path)

    def test_sanitizes_private_messages(self):
        """Imported counts and hash survive while raw page text is removed."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'output.xml'
            path.write_text('<robot><test id="s1-t1" name="SH-CUST-L01 A"><status status="FAIL">private-secret-value</status></test></robot>')
            result = REPORT.import_results(path)
            self.assertEqual(result['totals'], {'PASS': 0, 'FAIL': 1})
            self.assertNotIn('private-secret-value', json.dumps(result))

    def test_image_timeout_is_classified_without_page_content(self):
        """A known automation stop can be summarized without claiming a shop defect."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'output.xml'
            path.write_text('<robot><test id="s1-t1" name="SH-CUST-Q01 A"><status status="FAIL">Timeout while waiting for .sl-wrapper:visible .sl-image img</status></test></robot>')
            result = REPORT.import_results(path)
            self.assertEqual(result['tests']['SH-CUST-Q01']['failure_kind'], 'image_wait_timeout')
            self.assertNotIn('.sl-wrapper', result['tests']['SH-CUST-Q01']['message'])

    def test_model_drift_is_rejected(self):
        """Stale documentary analysis cannot silently accompany a changed model."""
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory)
            folder = app / 'tests/data'
            folder.mkdir(parents=True)
            (folder / 'CUSTOMER_DESIGN.yaml').write_text('schema_version: 1\nfault_policy: multi\n')
            with self.assertRaisesRegex(ValueError, 'fault_policy'): REPORT.prepare_report(app)

    def test_price_ambiguity_is_an_automation_failure(self):
        """Classify the supplied price-locator failure without retaining page details."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'output.xml'
            path.write_text('<robot><test id="s1-t1" name="SH-CUST-Q01 Quantity"><status status="FAIL">strict mode violation: product-price strong matched three elements</status></test></robot>')
            result = REPORT.import_results(path)
            self.assertEqual(result['tests']['SH-CUST-Q01']['failure_kind'], 'test_selector')
            self.assertEqual(result['tests']['SH-CUST-Q01']['failure_stage'], 'product_price')

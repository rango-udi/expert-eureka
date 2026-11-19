"""Exercise extension data/report contracts and password recovery control flow."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / 'apps/shuup'
for path in (APP, ROOT/'test-design'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
from scripts.customer_extensions import extension_cases, extension_records
from scripts.customer_report_data import prepare_report, import_results
from scripts.customer_design import read_reference
from test_design.specification import load_specification

SPEC = importlib.util.spec_from_file_location('extension_keywords', APP/'tests/robot/CustomerExtensions.py')
UI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UI)


class CustomerExtensionTests(unittest.TestCase):
    """Separate isolated contract/recovery checks from unexecuted browser claims."""

    def setUp(self):
        """Read the literal source model, without creating users or changing passwords."""
        self.model = load_specification(APP/'tests/data/CUSTOMER_DESIGN.yaml')

    def test_thirty_cases_have_bidirectional_literal_input_traceability(self):
        """Every new execution maps to exactly one localized/English business record."""
        cases = extension_cases(self.model)
        english = extension_records(self.model, read_reference('catalogue'))
        manual = extension_records(self.model, read_reference('catalogue'), 'vi')
        self.assertEqual(len(cases), 30)
        self.assertEqual({stage:sum(c['stage']==stage for c in cases) for stage in ('basket_update','address_book','password_change')},
                         {'basket_update':12,'address_book':11,'password_change':7})
        for case, en, vi in zip(cases, english, manual):
            self.assertEqual(en['robot_ids'], [case['id']])
            self.assertEqual(en['id'], vi['id'])
            self.assertEqual(set(en['analysis'].split(', ')), set(case['covers']))
            self.assertTrue(en['title'].isascii())
            self.assertFalse(vi['title'].isascii())
            self.assertIn(case['inputs']['account']['password'], en['input'])
            self.assertIn(case['inputs']['account']['password'], vi['input'])
            self.assertNotIn('${', vi['input'])

    def test_address_boundaries_and_every_analysis_rule_have_witnesses(self):
        """BVA, EP and decision tables point to actual new cases and no orphan rules."""
        data = prepare_report()
        obligations = {r[0] for r in data['extra_bva']} | {r[0] for r in data['ep']}
        obligations |= {rule for table in data['decisions'] for rule in table['rules']}
        covered = {part for row in data['cases'] for part in row['analysis'].split(', ')}
        self.assertTrue(obligations <= covered)
        title_rows = [r for r in data['extra_bva'] if r[0].startswith('BVA-SD-')]
        self.assertEqual([r[2] for r in title_rows], [13,0,1,2,254,255,256])
        self.assertTrue(all(row['evidence']=='' for row in data['cases']))

    def test_data_drift_and_unbound_operations_fail_before_generation(self):
        """Reject typo operations, credential drift, tokens and changed boundary vectors."""
        mutations = [lambda m:m['extensions']['cases'][0].update(operation='invented'),
                     lambda m:m['extensions']['cases'][0]['inputs']['account'].update(password='Changed!123'),
                     lambda m:m['extensions']['cases'][0]['inputs'].update(value='${quantity}'),
                     lambda m:m['extensions']['cases'][0]['inputs'].update(value='-1'),
                     lambda m:m['extensions']['accounts'][1].update(username='grace.mitchell')]
        for mutate in mutations:
            model=copy.deepcopy(self.model)
            mutate(model)
            with self.assertRaises(ValueError):extension_cases(model)

    def spy(self, recovery_error=False):
        """Record genuine password-flow branches while replacing only UI boundaries."""
        ui = UI.CustomerExtensionKeywords()
        events = []
        ui.robot=SimpleNamespace(log=lambda *args:events.append(('warn',args)))
        ui._extra_login=lambda *args:events.append(('login',args))
        ui._extra_password_page=lambda:None
        ui._extra_password_submit=lambda *args:events.append(('submit',args))
        ui._kw=lambda *args:events.append(('keyword',args))
        ui._logout=lambda:events.append(('logout',))
        ui._login=lambda *args:events.append(('old-login',args))
        ui._until=lambda probe,label:self.assertTrue(probe(),label)
        ui._visible=lambda *args:True
        ui._count=lambda *args:0
        ui._capture=lambda *args,**kwargs:events.append(('capture',args))
        def restore(inputs):
            """Model successful recovery or a failure while preserving original errors."""
            events.append(('restore',))
            if recovery_error:raise AssertionError('simulated recovery failure')
        ui._extra_restore_password=restore
        return ui,events

    def test_successful_change_checks_old_password_and_restores_original(self):
        """The flow verifies old rejection before restoring and capturing original access."""
        case=next(c for c in extension_cases(self.model) if c['id']=='SH-CUST-P06')
        ui,events=self.spy()
        ui._password_change(case)
        names=[e[0] for e in events]
        self.assertLess(names.index('old-login'),names.index('restore'))
        self.assertEqual(names.count('restore'),1)
        self.assertEqual(events[-1][1][1],'original-password-restored')

    def test_password_recovery_preserves_the_original_assertion(self):
        """A failed old-password oracle captures first and attempts recovery without masking it."""
        case=next(c for c in extension_cases(self.model) if c['id']=='SH-CUST-P06')
        ui,events=self.spy(recovery_error=True)
        ui._count=lambda *args:1
        with self.assertRaisesRegex(AssertionError,'old password still authenticates'):
            ui._password_change(case)
        names=[e[0] for e in events]
        self.assertLess(names.index('capture'),names.index('restore'))
        self.assertIn('warn',names)

    def test_new_execution_ids_survive_xml_import(self):
        """New basket/address/password results remain distinct when joined to reports."""
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'output.xml'
            path.write_text('<robot>'+''.join('<test name="'+rid+' Scenario"><status status="PASS"/></test>' for rid in ['SH-CUST-B12','SH-CUST-A11','SH-CUST-P07'])+'</robot>')
            self.assertEqual(set(import_results(path)['tests']),{'SH-CUST-B12','SH-CUST-A11','SH-CUST-P07'})

    def test_basket_selector_matches_native_card_and_exact_text_heading(self):
        """Evaluate the selector's structural subset against the pinned native DOM fixture."""
        import re
        import xml.etree.ElementTree as ET
        tree=ET.parse(ROOT/'tests/fixtures/shuup_basket_cards.html').getroot()
        def descendants(nodes, token):
            """Resolve descendant tag/class tokens against actual fixture elements."""
            tag, _, name=token.partition('.')
            return [element for node in nodes for element in node.iter()
                    if element is not node and (not tag or element.tag==tag)
                    and (not name or name in element.get('class','').split())]
        def count(selector):
            """Support the exact-text/has subset used here without claiming a Browser run."""
            outer, inner=selector.removeprefix('css=').split(':has(',1)
            root_id, *parts=outer.split()
            nodes=[element for element in tree.iter() if element.get('id')==root_id[1:]]
            for token in parts:nodes=descendants(nodes,token)
            path, value=inner.rsplit(':text-is(',1)
            expected=json.loads(value[:-2])
            matches=0
            for node in nodes:
                selected=[node]
                for token in path.split():selected=descendants(selected,token)
                matches+=int(any(''.join(element.itertext())==expected for element in selected))
            return matches
        ui=UI.CustomerExtensionKeywords()
        ui.catalogue={'rose':{'name':'Rose Nocturne'}}
        ui._kw=Mock()
        ui._count=count
        selector=ui._extra_basket_line('rose')
        self.assertEqual(count(selector),1)
        self.assertEqual(count(selector.replace('.single-item','tr')),0)

    def test_basket_card_cardinality_fails_before_mutation(self):
        """Missing/ambiguous cards produce actionable failures before quantity/delete actions."""
        ui=UI.CustomerExtensionKeywords()
        ui.catalogue={'rose':{'name':'Rose Nocturne'}}
        ui._kw=Mock()
        for count in (0,2):
            ui._count=lambda selector:count
            with self.assertRaisesRegex(AssertionError,'found '+str(count)+'.*no quantity/delete action'):
                ui._extra_basket_line('rose')

    def test_imported_basket_timeouts_are_selector_evidence(self):
        """A failed locator does not become an observed quantity or stock failure."""
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'output.xml'
            path.write_text('<robot><test name="SH-CUST-B01 Update"><status status="FAIL">TimeoutError: waiting for #update_basket_form tr:has(a.product-name:text-is(Rose)) input.line_quantity</status></test></robot>')
            result=import_results(path)['tests']['SH-CUST-B01']
            self.assertEqual(result['failure_kind'],'test_selector')
            self.assertEqual(result['failure_stage'],'basket_card')
            self.assertIsNone(result['observed_basket_count'])

    def test_unobserved_rejection_records_saved_quantity_without_passing(self):
        """An unobserved error preserves a screenshot and reports persisted acceptance/missing line."""
        case={'business_id':'TC-GB-009','inputs':{'value':'1.5'}}
        for actual in ['1.5','missing product line']:
            ui=UI.CustomerExtensionKeywords()
            events=[]
            ui._until=Mock(side_effect=AssertionError('timeout'))
            ui._quantity_error=lambda:False
            ui._capture=lambda *args,**kwargs:events.append('capture')
            ui._count=lambda *args:actual!='missing product line'
            ui._kw=lambda name,*args:events.append(name) or actual
            with self.assertRaisesRegex(AssertionError,'saved quantity after reload='+actual):
                ui._extra_update_rejection(case,'css=input.line_quantity')
            self.assertLess(events.index('capture'),events.index('Reload'))

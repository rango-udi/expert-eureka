"""Validate screenshot persistence, run matching and exact business-case attachments."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / 'apps/shuup'
if str(APP) not in sys.path:
    sys.path.insert(0,str(APP))
from scripts.customer_evidence import EvidenceRun, verified_images, PNG_HEADER
from scripts.customer_report_data import import_results, prepare_report
from test_design.specification import load_specification, semantic_hash


class CustomerEvidenceTests(unittest.TestCase):
    """Use isolated image fixtures, never represent them as real browser screenshots."""

    def fixture(self, app, robot_id='SH-CUST-Q06', case_id='TC-GH-006', status='FAIL'):
        """Create disposable PNG-shaped bytes and metadata for attachment validation."""
        model = load_specification(APP/'tests/data/CUSTOMER_DESIGN.yaml')
        run = EvidenceRun(app,semantic_hash(model))
        target = run.target(case_id,'failure')
        target.write_bytes(PNG_HEADER+b'unit-test-only-not-a-browser-image')
        run.record(target,case_id,robot_id,'failure','failure')
        run.finish_test(robot_id,status)
        results = {'schema_version':1,'source_sha256':'a'*64,'tests':{robot_id:{'status':status}},
                   'evidence_run':{'run_id':run.run_id,'manifest':run.manifest_path.relative_to(app).as_posix(),'model_sha256':run.data['model_sha256']}}
        return run,target,results

    def test_failed_quantity_image_fills_its_exact_business_row(self):
        """A Q06 screenshot belongs to TC-GH-006 without spreading to neighboring cases."""
        with tempfile.TemporaryDirectory() as folder:
            app=Path(folder)
            run,target,results=self.fixture(app)
            images,warnings=verified_images(app,results,run.data['model_sha256'])
            self.assertEqual(set(images),{'TC-GH-006'})
            self.assertEqual(warnings,[])
            self.assertEqual(images['TC-GH-006'][0]['path'],target.relative_to(app).as_posix())

    def test_report_uses_existing_image_in_both_presentations(self):
        """Excel and English JSON receive the same verified app-relative file path."""
        import shutil
        with tempfile.TemporaryDirectory() as folder:
            app=Path(folder)
            shutil.copytree(APP/'tests/data',app/'tests/data')
            run,target,results=self.fixture(app)
            data=prepare_report(app,results=results)
            row=next(row for row in data['cases'] if row['id']=='TC-GH-006')
            self.assertEqual(row['evidence'],target.relative_to(app).as_posix())
            self.assertEqual(next(row for row in data['_english_report']['cases'] if row['id']=='TC-GH-006')['evidence'],row['evidence'])
            self.assertEqual(row['actual'],data['labels']['not_run'])
            self.assertFalse(next(row for row in data['cases'] if row['id']=='TC-GH-005')['evidence'])

    def test_journey_image_is_not_copied_to_unreached_checkpoints(self):
        """An E01 failure image only attaches to the explicit checkpoint listed in its manifest."""
        with tempfile.TemporaryDirectory() as folder:
            app=Path(folder)
            run,target,results=self.fixture(app,'SH-CUST-E01','TC-DC-003')
            images,warnings=verified_images(app,results,run.data['model_sha256'])
            self.assertEqual(set(images),{'TC-DC-003'})
            self.assertNotIn('TC-LS-001',images)

    def test_missing_tampered_and_other_run_images_are_rejected(self):
        """Never fabricate links or attach a stale image solely because its TC ID matches."""
        with tempfile.TemporaryDirectory() as folder:
            app=Path(folder)
            run,target,results=self.fixture(app)
            target.write_bytes(PNG_HEADER+b'changed')
            self.assertEqual(verified_images(app,results,run.data['model_sha256'])[0],{})
            target.unlink()
            self.assertEqual(verified_images(app,results,run.data['model_sha256'])[0],{})
            self.assertEqual(verified_images(app,results,'b'*64)[0],{})
            results['evidence_run']['manifest']='../outside.json'
            self.assertEqual(verified_images(app,results,run.data['model_sha256'])[0],{})

    def test_legacy_xml_has_no_invented_screenshots(self):
        """An old output.xml without capture metadata remains log-only evidence."""
        with tempfile.TemporaryDirectory() as folder:
            app=Path(folder)
            path=app/'output.xml'
            path.write_text('<robot><suite><test name="SH-CUST-Q06 Quantity"><status status="FAIL"/></test></suite></robot>')
            results=import_results(path)
            self.assertIsNone(results['evidence_run'])
            self.assertEqual(verified_images(app,results,'a'*64)[0],{})

    def test_xml_import_retains_screenshot_provenance(self):
        """The chosen source XML identifies its exact screenshot run and model."""
        with tempfile.TemporaryDirectory() as folder:
            app=Path(folder)
            run,target,results=self.fixture(app)
            path=app/'output.xml'
            path.write_text('<robot><suite><test name="SH-CUST-Q06 Quantity"><status status="FAIL"/></test><meta name="Model SHA256">'+run.data['model_sha256']+'</meta><meta name="Evidence Run ID">'+run.run_id+'</meta><meta name="Evidence Manifest">'+run.manifest_path.relative_to(app).as_posix()+'</meta></suite></robot>')
            parsed=import_results(path)
            self.assertEqual(parsed['evidence_run'],results['evidence_run'])
            self.assertTrue(verified_images(app,parsed,run.data['model_sha256'])[0])

    def test_every_business_case_has_an_actual_capture_binding(self):
        """Twenty journey cases plus independent probes cover all 41 business IDs."""
        definitions=json.loads((APP/'tests/data/CUSTOMER_CASE_TEXT.json').read_text())['cases']
        definitions += json.loads((APP/'tests/data/CUSTOMER_EXTENSION_TEXT.json').read_text())['cases']
        expected={row['id'] for row in definitions}
        source=(APP/'tests/robot/CustomerJourney.py').read_text()
        tree=ast.parse(source)
        bound={node.value for node in ast.walk(tree) if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value in expected}
        independent={row['id'] for row in definitions if row['robot_ids']!=['SH-CUST-E01']}
        self.assertIn("business_id = 'TC-VC-'",source)
        from scripts.customer_design import read_reference
        carriers={'TC-VC-'+str(index).zfill(3) for index,_ in enumerate(read_reference('partners')['carriers'],1)}
        self.assertEqual(bound|independent|carriers,expected)

    def test_capture_failure_does_not_replace_original_ui_failure(self):
        """A screenshot adapter error is recorded without being raised by the capture helper."""
        tree=ast.parse((APP/'tests/robot/CustomerJourney.py').read_text())
        cls=next(node for node in tree.body if isinstance(node,ast.ClassDef))
        method=next(node for node in cls.body if isinstance(node,ast.FunctionDef) and node.name=='_capture')
        namespace={}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'<capture-dispatch>','exec'),namespace)
        failures=[]
        def fail(*args):
            """Model a page that cannot be screenshotted after its failure."""
            raise RuntimeError('capture failed')
        evidence=SimpleNamespace(target=lambda *args:Path('/unused.png'),capture_error=lambda *args:failures.append(args))
        spy=SimpleNamespace(evidence=evidence,_kw=fail,active_robot_id='SH-CUST-Q06',robot=SimpleNamespace(log=lambda *args:None))
        namespace['_capture'](spy,['TC-GH-006'],'failure','failure')
        self.assertEqual(len(failures),1)

    def test_legacy_source_path_is_log_only_fallback(self):
        """An existing source file fills evidence without pretending it is a screenshot."""
        import shutil
        with tempfile.TemporaryDirectory() as folder:
            app=Path(folder)
            shutil.copytree(APP/'tests/data',app/'tests/data')
            (app/'reports').mkdir()
            (app/'reports/output.xml').write_text('<robot/>')
            results={'tests':{'SH-CUST-Q06':{'status':'FAIL'}},'source_path':'reports/output.xml'}
            data=prepare_report(app,results=results)
            row=next(row for row in data['cases'] if row['id']=='TC-GH-006')
            self.assertEqual(row['evidence'],'reports/output.xml')
            self.assertEqual(data['screenshot_count'],0)
            self.assertTrue(data['evidence_warnings'])

    def test_original_failure_captures_page_before_propagation(self):
        """The exception handler captures the active case before Robot can run Close Browser."""
        import base64
        from test_design.specification import semantic_hash
        tree=ast.parse((APP/'tests/robot/CustomerJourney.py').read_text())
        cls=next(node for node in tree.body if isinstance(node,ast.ClassDef))
        method=next(node for node in cls.body if isinstance(node,ast.FunctionDef) and node.name=='execute_customer_case')
        method.decorator_list=[]
        events=[]
        robot=SimpleNamespace(get_library_instance=lambda *args:object())
        namespace={'json':json,'base64':base64,'semantic_hash':semantic_hash,'Path':Path,
                   'BuiltIn':lambda:robot,'__file__':str(APP/'tests/robot/CustomerJourney.py')}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'<evidence-failure-lifecycle>','exec'),namespace)
        case={'id':'SH-CUST-Q06','stage':'quantity','expected':'rejected','value':'26'}
        def fail(*args):
            """Produce the original functional failure after a page has been opened."""
            raise AssertionError('original quantity failure')
        spy=SimpleNamespace(base='http://store.test',model={'_provenance':{'case_sha256':{case['id']:semantic_hash(case)}}},
                            evidence=SimpleNamespace(finish_test=lambda *args:events.append(('finish',args))),
                            _kw=lambda *args:events.append(('keyword',args)),_quantity=fail,
                            _capture=lambda *args,**kwargs:events.append(('capture',args,kwargs)))
        def at(ids):
            """Track the active business case selected by the actual executor."""
            spy.active_business_cases=ids
        spy._at=at
        payload=base64.b64encode(json.dumps(case).encode()).decode()
        with self.assertRaisesRegex(AssertionError,'original quantity failure'):
            namespace['execute_customer_case'](spy,payload)
        capture=next(index for index,row in enumerate(events) if row[0]=='capture')
        finish=next(index for index,row in enumerate(events) if row[0]=='finish')
        self.assertLess(capture,finish)
        self.assertEqual(events[capture][1][0],['TC-GH-006'])
        self.assertEqual(events[capture][2]['role'],'failure')

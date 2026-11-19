"""Prepare documentary report data and import Robot evidence without executing tests."""
import copy
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import sys
# Host import, direct script and container execution use the same report contract.
_app = Path(__file__).resolve().parents[1]
if str(_app) not in sys.path:
    sys.path.insert(0, str(_app))
from scripts.customer_report_contract import report_contract
from scripts.customer_evidence import verified_images
APP = Path(__file__).resolve().parents[1]

def read_json(path):
    """Read a UTF-8 report/model document; no app or browser modules are imported."""
    return json.loads(Path(path).read_text(encoding='utf-8'))

def import_results(path):
    """Import one run, retaining stable IDs and redacting page/credential details."""
    path = Path(path)
    if path.suffix.lower() == '.json':
        result = read_json(path)
        if result.get('schema_version') != 1 or not isinstance(result.get('tests'), dict) or (not re.fullmatch('[a-f0-9]{64}', result.get('source_sha256', ''))):
            raise ValueError('Use a schema_version 1 sanitized customer report with a SHA-256 source hash.')
        if any((row.get('status') not in ('PASS', 'FAIL', 'SKIP') for row in result['tests'].values())):
            raise ValueError('Customer result status must be PASS, FAIL or SKIP.')
        return result
    payload = path.read_bytes()
    if len(payload) > 25 * 1024 * 1024 or b'<!DOCTYPE' in payload.upper():
        raise ValueError('Use a Robot XML file without DTD, up to 25 MiB.')
    root = ET.fromstring(payload)
    results = {}
    for test in root.iter('test'):
        case_id = test.get('name', '').split(' ', 1)[0]
        if not re.fullmatch('SH-CUST-(?:[RLQBAP][0-9]{2}|E01)', case_id):
            continue
        if case_id in results:
            raise ValueError('Duplicate customer ID in one Robot output: ' + case_id)
        status = test.find('status')
        if status is None:
            continue
        message = status.text or ''
        accepted_quantity = re.search(r'basket now contains ([0-9]+) items', message) if status.get('status') == 'FAIL' else None
        image_timeout = status.get('status') == 'FAIL' and 'Timeout' in message and '.sl-image img' in message
        price_selector = "product-price" in message and "strict mode violation" in message
        basket_selector = status.get('status') == 'FAIL' and 'Timeout' in message and '#update_basket_form tr:has(a.product-name' in message
        selector_error = status.get('status') == 'FAIL' and ("locator('h1')" in message or price_selector) and ('strict mode violation' in message)
        results[case_id] = {'status': status.get('status'), 'anchor': test.get('id'), 'observed_basket_count': int(accepted_quantity[1]) if accepted_quantity else None, 'failure_kind': 'above_stock_accepted' if accepted_quantity else 'test_selector' if selector_error or basket_selector else 'image_wait_timeout' if image_timeout else None, 'failure_stage': 'basket_card' if basket_selector else 'product_price' if price_selector else 'first_product_heading' if selector_error and '>The One</h1>' in message else None, 'message': 'Above-stock quantity was accepted into the basket.' if accepted_quantity else 'Basket selector expected a table row instead of the native product card.' if basket_selector else 'Product price selector matched multiple elements.' if price_selector else 'Responsive heading selector matched two elements.' if selector_error else 'Timed out waiting for the enlarged product photograph.' if image_timeout else 'Passed in imported execution.' if status.get('status') == 'PASS' else 'Execution failed; inspect the private original Robot log.'}
    if not results:
        raise ValueError('No customer case IDs were found; this is not a customer execution report.')
    metadata = {item.get('name'): item.text or '' for item in root.iter('meta')}
    evidence_run = {'run_id': metadata.get('Evidence Run ID'), 'manifest': metadata.get('Evidence Manifest'),
                    'model_sha256': metadata.get('Model SHA256')} if metadata.get('Evidence Run ID') else None
    return {'evidence_run': evidence_run, 'schema_version': 1, 'generated': root.get('generated'), 'source_sha256': hashlib.sha256(payload).hexdigest(), 'unique_execution_count': 1, 'tests': results, 'totals': {value: sum((row['status'] == value for row in results.values())) for value in ('PASS', 'FAIL')}, 'note': 'Imported execution, not a rerun of repaired code. No credentials or raw page data retained.'}

def prepare_report(app=APP, results=None, evidence_path='', model_path=None):
    """Prepare business scenarios; imported Robot runs remain separate reference evidence.

    A business case may have several design obligations and related automation
    probes. A Robot PASS cannot certify the newly written scenario or its exact
    example inputs, so actual outcomes are never inferred from automation IDs.
    """
    app = Path(app)
    data = report_contract(app, model_path=model_path)
    data['results'] = results
    data['trace'] = []
    labels = data['labels']
    images, warnings = verified_images(app, results, data['model_sha256'])
    data['evidence_warnings'] = warnings
    known = {row['id']: set(row['robot_ids']) for row in data['cases']}
    images = {case_id: [image for image in rows if image['robot_id'] in known[case_id]]
              for case_id, rows in images.items() if case_id in known}
    data['screenshot_count'] = sum(len(rows) for rows in images.values())
    if results:
        data['guide'].append(['\u1ea2nh giao di\u1ec7n', '\u0110\u00e3 x\u00e1c minh ' + str(data['screenshot_count']) + ' \u1ea3nh UI t\u1eeb l\u1ea7n ch\u1ea1y ngu\u1ed3n. \u0110\u01b0\u1eddng d\u1eabn \u1ea3nh \u0111\u01b0\u1ee3c g\u1eafn theo t\u1eebng TC. Khi ch\u01b0a c\u00f3 \u1ea3nh, c\u1ed9t B\u1eb1ng ch\u1ee9ng d\u1eabn \u0111\u1ebfn b\u00e1o c\u00e1o ngu\u1ed3n; c\u1ea7n ch\u1ea1y l\u1ea1i b\u1ed9 c\u00f3 ch\u1ee9c n\u0103ng ch\u1ee5p \u1ea3nh \u0111\u1ec3 b\u1ed5 sung \u1ea3nh th\u1eadt.'])
    source_path = (results or {}).get('source_path', '')
    source = app / source_path
    source_link = source_path if source_path and not Path(source_path).is_absolute() and '..' not in Path(source_path).parts and source.is_file() and app.resolve() in source.resolve().parents else ''
    for row in data['cases']:
        row.update(actual=labels['not_run'], severity=labels['not_applicable'],
                   reproducibility=labels['not_repeated'], evidence='',
                   reporter='', status=labels['new'])
        attachments = [image['path'] for image in images.get(row['id'], []) if image['robot_id'] in row['robot_ids']]
        row['evidence'] = '\n'.join(dict.fromkeys(attachments))
        if not attachments and source_link and any(identifier in (results or {}).get('tests', {}) for identifier in row['robot_ids']):
            row['evidence'] = source_link
        # Keep the English non-Excel export consistent with the same verified paths.
        english_row = next(item for item in data['_english_report']['cases'] if item['id'] == row['id'])
        english_row['evidence'] = row['evidence']
        observed = []
        links = []
        for robot_id in row['robot_ids']:
            result = (results or {}).get('tests', {}).get(robot_id)
            if result:
                summary = data['trace_status_labels'][result['status']]
                if result.get('failure_kind') == 'test_selector':
                    summary += '; ' + data['trace_selector_note']
                observed.append(robot_id + ': ' + result['status'] + ' - ' + summary)
                if evidence_path:
                    links.append(evidence_path + '#' + robot_id)
        data['trace'].append([
            row['id'], row['requirement'] + ': ' + data['requirements'][row['requirement']],
            row['analysis'], ', '.join(row['robot_ids']),
            '; '.join(observed) if observed else labels['trace_unrun'], '\n'.join(links)])
    data['case_count'] = len(data['cases'])
    data['automation_count'] = len({identifier for row in data['cases'] for identifier in row['robot_ids']})
    return data

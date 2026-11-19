"""Export a reduced, traceable customer UI suite without importing Django.

The numeric proposals come from the shared single-fault engine. Registration
and login partitions are explicit stage-specific negative probes. One complete
journey witnesses all declared positive workflow and decision checkpoints.
Generation never claims that those checkpoints have passed on a browser.
"""
import argparse
import base64
import csv
import fnmatch
import json
from decimal import Decimal
from pathlib import Path
import sys

# A direct script starts with /app/scripts on sys.path, so add its package root.
APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
from test_design.specification import load_specification, semantic_hash

QUANTITY_IDS = {
    "bva:quantity:below": "Q01", "bva:quantity:min": "Q02", "bva:quantity:min-plus": "Q03",
    "bva:quantity:max-minus": "Q04", "bva:quantity:max": "Q05", "bva:quantity:above": "Q06",
    "baseline": "Q07", "ep:quantity:missing": "Q08", "ep:quantity:fraction": "Q09"}

DECISION_RULE_IDS = frozenset(["D-C01", "D-C02", "D-C03", "D-C04", "D-A01", "D-A02",
                               "D-S01", "D-S02", "D-S03", "D-T01", "D-T02"])


def read_reference(name):
    """Read the shared, read-only fixture specification rather than copy its records."""
    root = Path('/fuzcake-data/records')
    if not root.exists():
        root = Path(__file__).resolve().parents[3] / 'fuzcake-data/records'
    return json.loads((root / (name + '.json')).read_text(encoding='utf-8'))


def validate_customer_model(model):
    """Reject metadata that the UI executor would ignore or interpret differently."""
    import re
    if model.get('schema_version') != 1 or model.get('fault_policy') != 'single':
        raise ValueError('Use customer schema_version 1 and fault_policy: single.')
    from scripts.customer_inputs import validate_test_data
    validate_test_data(model)
    if not isinstance(model.get('negative_cases'), list):
        raise ValueError('negative_cases must be a list.')
    for row in model['negative_cases']:
        if not isinstance(row.get('value'), str):
            raise ValueError('Negative UI values must be quoted strings.')
        if not row.get('covers') or not all(isinstance(item, str) for item in row['covers']):
            raise ValueError('Every negative case needs explicit coverage IDs.')
        stage, field, value = row.get('stage'), row.get('field'), row['value']
        if '$' in value or '<' in value or '>' in value:
            raise ValueError('Negative UI values must be literal data, without interpolation tokens.')
        if not re.fullmatch(r'SH-CUST-[RL][0-9]{2}', row.get('id', '')):
            raise ValueError('Use stable SH-CUST-Rxx/Lxx negative case IDs.')
        if row['id'][8] != {'registration': 'R', 'login': 'L'}.get(stage):
            raise ValueError('Case ID must match its executable stage.')


def build_plan(model, catalogue, store, partners):
    """Union engine obligations with stage partitions and a complete UI journey.

    Every selected negative probe changes one input field. Unique real coverage
    obligations identify mandatory candidates. The cardinality
    bound concerns these finite candidates and their independent-stage policy,
    not a global minimum over every possible browser script.
    """
    from test_design.engine import design
    validate_customer_model(model)

    products = {row['sku']: row for row in catalogue['products']}
    assert_ids = [model['quantity_product']] + model['order_products']
    if len(set(model['order_products'])) != 3 or not all(sku in products for sku in assert_ids):
        raise ValueError('Declare three distinct existing order products and one quantity product.')
    addresses = {row['id'] for row in store['addresses']}
    if not {model['billing_address'], model['shipping_address']} <= addresses:
        raise ValueError('Use existing shared address identifiers.')
    if set(model['quantity_model']['fields']) != {'quantity'}:
        raise ValueError('Add executable UI bindings before adding new numeric fields.')
    rules = [rule['id'] for rule in model['decision_rules']]
    if len(rules) != len(DECISION_RULE_IDS) or set(rules) != DECISION_RULE_IDS:
        raise ValueError('Update executable customer checkpoints before changing decision-rule IDs.')
    field = model['quantity_model']['fields']['quantity']
    if Decimal(field['max']) != products[model['quantity_product']]['stock']:
        raise ValueError('The quantity upper bound must match the declared initial fixture stock.')
    if model['quantity_product'] in model['order_products']:
        raise ValueError('Keep the boundary product separate from products consumed by the order.')
    if len(partners['carriers']) != 3 or any(Decimal(row['fee']) < 0 for row in partners['carriers']):
        raise ValueError('The customer model requires the three declared nonnegative carrier fees.')
    if model['final_carrier'] not in {row['id'] for row in partners['carriers']}:
        raise ValueError('Choose the final carrier from the shared partner specification.')
    numeric = design(model['quantity_model'])
    cases = []
    for row in numeric['cases']:
        value = row['inputs']['quantity']
        matches = [short_id for obligation, short_id in QUANTITY_IDS.items() if obligation in row['covers']]
        if not matches:
            raise ValueError('Assign a stable ID to every new coverage obligation.')
        case_id = 'SH-CUST-' + matches[0]
        cases.append({'id': case_id, 'stage': 'quantity', 'value': value,
                      'title': 'Quantity ' + (value or 'empty'), 'expected': row['expected'],
                      'description': 'Search ' + products[model['quantity_product']]['name'] + ', enter one quantity, inspect native rejection or basket quantity.',
                      'covers': row['covers']})
    for row in model['negative_cases']:
        if row['stage'] not in ('registration', 'login') or row['expected'] != 'rejected':
            raise ValueError('Declare an explicit registration or login rejection probe.')
        allowed = {'registration': {'username', 'email', 'password1', 'password2'}, 'login': {'username', 'password'}}
        if row['field'] not in allowed[row['stage']]:
            raise ValueError('Bind each negative field to an existing native form input.')
        case = dict(row)
        case['covers'] = row['covers']
        cases.append(case)
    journey = {'id': 'SH-CUST-E01', 'stage': 'e2e', 'title': 'Customer Registers Searches Three Products And Places COD Order',
               'expected': 'order_received_not_paid',
               'description': 'Register, activate by delivered mail, log in, search three products, inspect, cart, coupon, addresses, shipping, COD and exact order history.',
               'covers': ['FLOW-registration', 'FLOW-activation', 'FLOW-login', 'FLOW-search-three',
                          'FLOW-product-details', 'FLOW-basket-three', 'FLOW-order-history',
                          'EP-registration-valid', 'EP-login-valid', 'EP-search-found', 'EP-search-no-match',
                          'EP-address-street-missing', 'EP-address-valid'] +
                         [rule['id'] for rule in model['decision_rules']]}
    cases.append(journey)
    # English execution prose and Vietnamese Excel prose share stable scenario IDs.
    prose = json.loads((APP_ROOT / 'tests/data/CUSTOMER_CASE_TEXT.json').read_text(encoding='utf-8'))
    for case in cases:
        row = next(row for row in prose['cases'] if row['robot_ids'] == [case['id']]
                   and (case['stage'] != 'e2e' or row['id'] == 'TC-HT-001'))
        case['title'], case['description'] = row['title'], row['description']
    from scripts.customer_inputs import materialize_inputs
    for case in cases:
        case['inputs'] = materialize_inputs(model, case, catalogue, store, partners)
    from scripts.customer_extensions import extension_cases
    cases.extend(extension_cases(model))
    cases.sort(key=lambda row: (row['stage'] == 'e2e', row['id']))
    if len({row['id'] for row in cases}) != len(cases):
        raise ValueError('Customer case IDs must be unique.')
    obligations = sorted({item for row in cases for item in row['covers']})
    # A candidate with an exclusively covered real obligation cannot be removed.
    mandatory = {row['id'] for row in cases if any(
        sum(obligation in other['covers'] for other in cases) == 1
        for obligation in row['covers'])}
    lower_bound = len(mandatory)
    return {'schema_version': 1, 'cases': cases, 'selected_count': len(cases),
            'candidate_count': len(cases), 'lower_bound': lower_bound,
            'minimum_proven_within_declared_candidates': lower_bound == len(cases),
            'minimum_scope': 'One independent negative probe per test; one continuous positive journey. This bound does not compare arbitrary combinations of several negative probes in one test.',
            'planned_obligations': obligations, 'planned_covered_obligations': obligations,
            'execution_status': 'not_executed', 'model_sha256': semantic_hash(model),
            'reference_sha256': {name: semantic_hash(data) for name, data in (('catalogue', catalogue), ('store', store), ('partners', partners))}, 'numeric_plan': numeric,
            'excluded_scope': model['scope_exclusions'], 'attribution': model['attribution']}


def export(model_path, output, case_patterns=None, stage=None):
    """Freeze the reviewed model and emit CSV, coverage, table and Robot suite."""
    model = load_specification(model_path)
    plan = build_plan(model, read_reference('catalogue'), read_reference('store'), read_reference('partners'))
    scheduled = [row for row in plan['cases'] if (stage is None or row['stage'] == stage) and
                 (not case_patterns or any(fnmatch.fnmatchcase(row['id'], pattern) for pattern in case_patterns))]
    if not scheduled:
        raise ValueError('No customer cases match the requested ID pattern/stage.')
    plan['scheduled_count'] = len(scheduled)
    plan['scheduled_ids'] = [row['id'] for row in scheduled]
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    snapshot = dict(model, _provenance={'model_sha256': plan['model_sha256'], 'reference_sha256': plan['reference_sha256'],
                                               'case_sha256': {row['id']: semantic_hash(row) for row in plan['cases']}})
    (output / 'model.json').write_text(json.dumps(snapshot, indent=2) + '\n', encoding='utf-8')
    (output / 'coverage.json').write_text(json.dumps(plan, indent=2) + '\n')
    with (output / 'robot_transport.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream, delimiter=';')
        writer.writerow(['*** Test Cases ***', '${payload}', '[Tags]', '[Documentation]'])
        for row in scheduled:
            payload = base64.b64encode(json.dumps(row).encode()).decode('ascii')
            writer.writerow([row['id'] + ' ' + row['title'], payload,
                             'customer,' + row['stage'] + (',single-fault' if row['stage'] != 'e2e' else ',journey'), row['description'] + ' Covers: ' + ', '.join(row['covers'])])
    from scripts.customer_english_cases import execution_records, english_report
    records = execution_records(model, scheduled)
    report = english_report(model, plan, read_reference('catalogue'))
    keys = ['id','title','module','description','preconditions','steps','input','expected','actual','severity','priority','reproducibility','evidence','reporter','status']
    with (output / 'execution_cases.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(report['headers'])
        writer.writerows([[row[key] for key in keys] for row in records])
    with (output / 'test_cases.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(report['headers'])
        writer.writerows([[row[key] for key in keys] for row in report['cases']])
    from scripts.customer_report_contract import report_contract
    localized = report_contract(APP_ROOT, model_path=model_path)
    prose = []
    for row in localized['cases']:
        prose.extend(['## ' + row['id'] + ' - ' + row['title'], '', row['description'], '',
                      row['preconditions'], '', row['steps'], '', row['input'], '', row['expected'], ''])
    (output / 'test_cases.md').write_text('\n'.join(prose), encoding='utf-8')
    (output / 'report_data.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (output / 'run.robot').write_text('''*** Settings ***
Documentation    Reduced customer specification. Generation is not browser execution.
Library    Browser
Library    ${CURDIR}/../../tests/robot/CustomerJourney.py    ${CURDIR}/model.json
Library    DataDriver    file=${CURDIR}/robot_transport.csv    dialect=userdefined    delimiter=;    encoding=utf-8
Test Template    Run Customer Case
Test Teardown    Close Browser
Test Tags    customer

*** Test Cases ***
Customer case placeholder
    unused

*** Keywords ***
Run Customer Case
    [Arguments]    ${payload}
    Execute Customer Case    ${payload}
''')
    suite = output / 'run.robot'
    suite.write_text(suite.read_text().replace('Documentation    Reduced', 'Metadata    Model SHA256    ' + plan['model_sha256'] + '\nDocumentation    Reduced'), encoding='utf-8')
    return plan


def main():
    """Generate the customer suite inside a prepared tools or browser container."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, default=Path('tests/data/CUSTOMER_DESIGN.yaml'))
    parser.add_argument('--output', type=Path, default=Path('reports/customer'))
    parser.add_argument('--case', action='append', dest='case_patterns', help='Stable case-ID pattern, repeatable.')
    parser.add_argument('--stage', choices=['registration', 'login', 'quantity', 'e2e', 'basket_update', 'address_book', 'password_change'])
    options = parser.parse_args()
    try:
        plan = export(options.model, options.output, options.case_patterns, options.stage)
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError) as error:
        parser.exit(2, 'Invalid customer design: ' + str(error) + '\n')
    print('Customer plan:', plan['selected_count'], 'cases;', plan['scheduled_count'], 'scheduled; generated, not executed. See', options.output / 'coverage.json')


if __name__ == '__main__':
    main()

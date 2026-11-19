"""Build Vietnamese manual test reports from literal customer execution data."""
import json
from decimal import Decimal
from pathlib import Path
import sys

# /app/scripts is shallower than the repository layout; derive from the app root.
APP_ROOT = Path(__file__).resolve().parents[1]
shared = APP_ROOT.parent.parent / 'test-design'
if shared.exists():
    sys.path.insert(0, str(shared))
from test_design.specification import load_specification
from scripts.customer_design import build_plan, read_reference
from scripts.customer_case_contract import prepare_business_cases


def report_contract(app, model_path=None):
    """Preserve the original scenarios and append reviewed customer extensions."""
    app = Path(app)
    model = load_specification(model_path or app / 'tests/data/CUSTOMER_DESIGN.yaml')
    catalogue, store, partners = [read_reference(name) for name in ('catalogue', 'store', 'partners')]
    plan = build_plan(model, catalogue, store, partners)
    data = json.loads((app / 'tests/data/CUSTOMER_EXCEL_TEXT.json').read_text(encoding='utf-8'))
    executions = {row['id']: row for row in plan['cases']}
    data['cases'] = prepare_business_cases(data, executions, catalogue)
    from scripts.customer_extensions import extension_records, extend_analysis
    data['cases'].extend(extension_records(model, catalogue, 'vi'))
    extend_analysis(data, model)
    data['model_sha256'] = plan['model_sha256']
    field = model['quantity_model']['fields']['quantity']
    data['bva'] = {key: float(field[key]) for key in ('min','max','step','nominal')}
    products = {row['sku']: row for row in catalogue['products']}
    subtotal = sum((Decimal(products[sku]['price']) for sku in model['order_products']), Decimal('0'))
    data['money_inputs'] = [float(subtotal), float(store['welcome_offer']['percentage'])] + [float(row['fee']) for row in partners['carriers']]
    journey = executions['SH-CUST-E01']['inputs']
    values = {'EP-DK-01': journey['registration']['username'], 'EP-DK-04': executions['SH-CUST-R03']['inputs']['username'],
              'EP-DK-05': journey['registration']['email'], 'EP-DK-07': executions['SH-CUST-R05']['inputs']['email'],
              'EP-DK-08': journey['registration']['password1'], 'EP-DK-10': journey['registration']['password2'],
              'EP-DK-12': executions['SH-CUST-R08']['inputs']['password2'],
              'EP-DN-01': journey['registration']['username'], 'EP-DN-03': executions['SH-CUST-L02']['inputs']['username'],
              'EP-DN-04': journey['registration']['password1'], 'EP-DN-06': executions['SH-CUST-L04']['inputs']['password'],
              'EP-TK-02': journey['absent_search']}
    for row in data['ep']:
        if row[0] in values:
            row[4] = values[row[0]]
    from scripts.customer_english_cases import english_report
    data['_english_report'] = english_report(model, plan, catalogue)
    return data

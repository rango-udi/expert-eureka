"""Render English execution artifacts while keeping literal inputs shared with Excel."""
import json
from decimal import Decimal
from pathlib import Path
from scripts.customer_case_contract import business_input
from test_design.specification import semantic_hash

APP = Path(__file__).resolve().parents[1]
HEADERS = ['Test case ID','Test case name','Module / Function','Description','Preconditions','Steps',
           'Test data / Input','Expected result','Actual result','Severity','Priority','Reproducibility',
           'Evidence','Reporter','Status']


def english_input(case_id, executions, catalogue):
    """Translate presentation labels only; every typed input value remains unchanged."""
    text = business_input(case_id, executions, catalogue)
    labels = {
        'Giao \u0111\u1ebfn \u0111\u1ecba ch\u1ec9 thanh to\u00e1n: Kh\u00f4ng':'Ship to billing address: No',
        'Giao \u0111\u1ebfn \u0111\u1ecba ch\u1ec9 thanh to\u00e1n: C\u00f3':'Ship to billing address: Yes',
        'Qu\u1ed1c gia c\u1ea3 hai \u0111\u1ecba ch\u1ec9':'Country for both addresses', 'V\u00f9ng: kh\u00f4ng ch\u1ecdn':'Region: unselected',
        'Kh\u00f4ng nh\u1eadp m\u00e3 gi\u1ea3m gi\u00e1.':'Coupon field: empty.', 'X\u00f3a m\u00e3 gi\u1ea3m gi\u00e1 \u0111\u00e3 \u00e1p d\u1ee5ng':'Remove applied coupon',
        'Ch\u1ecdn \u0111\u01a1n v\u1eeba \u0111\u1eb7t c\u1ee7a':'Select the latest order for', 'Nh\u1eadp l\u1ea1i m\u1eadt kh\u1ea9u':'Confirm password',
        'T\u00ean \u0111\u0103ng nh\u1eadp':'Username','M\u1eadt kh\u1ea9u':'Password','\u0110\u1ec3 tr\u1ed1ng':'Empty','S\u1ea3n ph\u1ea9m':'Product',
        '\u0110\u01a1n gi\u00e1':'Unit price','C\u00f2n b\u00e1n':'Stock','S\u1ed1 l\u01b0\u1ee3ng nh\u1eadp':'Entered quantity','L\u1ea7n ':'Search ',
        'T\u1eeb kh\u00f3a':'Search term','M\u00f4 t\u1ea3':'Description','M\u00e3 gi\u1ea3m gi\u00e1':'Coupon','M\u1ee9c gi\u1ea3m':'Discount',
        '10% ti\u1ec1n h\u00e0ng':'10% of product subtotal','Ng\u01b0\u1eddi nh\u1eadn':'Recipient','\u0110i\u1ec7n tho\u1ea1i':'Phone',
        '\u0110\u01b0\u1eddng':'Street','\u0110\u1ecba ch\u1ec9 b\u1ed5 sung':'Street line 2','Th\u00e0nh ph\u1ed1':'City','M\u00e3 b\u01b0u ch\u00ednh':'Postal code',
        'Qu\u1ed1c gia':'Country','Thanh to\u00e1n':'Payment','Giao h\u00e0ng':'Delivery','Ph\u00ed giao h\u00e0ng':'Delivery fee',
        'Ti\u1ec1n sau gi\u1ea3m gi\u00e1':'Discounted subtotal','T\u1ed5ng ti\u1ec1n':'Total','ch\u01b0a thanh to\u00e1n':'not paid',
        '\u0110\u1ed3ng \u00fd \u0111i\u1ec1u kho\u1ea3n':'Terms accepted','Ghi ch\u00fa':'Comment','C\u00f3':'Yes','Kh\u00f4ng':'No','chai':'bottle(s)'}
    for old in sorted(labels, key=len, reverse=True):
        text = text.replace(old, labels[old])
    billing = executions['SH-CUST-E01']['inputs']['billing']['street']
    text = text.replace('v\u00f9ng: kh\u00f4ng ch\u1ecdn', 'region: unselected')
    text = text.replace('thanh to\u00e1n:', 'payment:')
    text = text.replace('Payment: ' + billing, 'Billing address: ' + billing)
    if not text.isascii():
        raise ValueError('Add an English input label before exporting ' + case_id)
    return text


def english_report(model, plan, catalogue):
    """Prepare original and extended English scenarios for CSV and JSON output."""
    source = json.loads((APP / 'tests/data/CUSTOMER_CASE_TEXT.json').read_text(encoding='utf-8'))
    executions = {row['id']: row for row in plan['cases']}
    journey = executions['SH-CUST-E01']['inputs']
    subtotal = sum((Decimal(row['price']) for row in journey['products']), Decimal('0'))
    discounted = (subtotal * (1 - Decimal(journey['coupon']['percentage']))).quantize(Decimal('0.01'))
    carrier = next(row for row in journey['carriers'] if row['id'] == journey['final_carrier'])
    total = discounted + Decimal(carrier['fee'])
    modules = {'DK':'Registration','DN':'Login','TK':'Product search','SP':'Product details','GH':'Basket',
               'KM':'Coupon','DC':'Checkout addresses','VC':'Delivery','DH':'Order placement','LS':'Order history','HT':'Customer journey'}
    records = []
    for definition in source['cases']:
        row = dict(definition)
        case_id, group = row['id'], row['id'].split('-')[1]
        row['module'] = modules[group]
        row['input'] = english_input(case_id, executions, catalogue)
        row['preconditions'] = 'Prepared local store with matching fixture prices, stock, coupon and delivery options; a fresh browser session.'
        if group == 'DK' and case_id != 'TC-DK-001':
            row['preconditions'] += ' The baseline username/email are unused; the documented existing customer is active.'
            row['steps'] = '1. Open Log in, then Register.\n2. Enter the four literal values shown in Input.\n3. Submit Register.\n4. Inspect the changed field and authentication state.'
            expected = 'The changed field has a native or server validation error; registration is rejected and the customer remains signed out.'
        elif group == 'DN' and case_id != 'TC-DN-001':
            row['preconditions'] += ' The documented existing customer is active; the unregistered login name is unused.'
            row['steps'] = '1. Open Log in.\n2. Enter the literal username and password shown in Input.\n3. Submit Log in.\n4. Inspect the login error and authentication state.'
            expected = 'Login is rejected with a native or server error; the customer remains signed out.'
        elif group == 'GH' and case_id != 'TC-GH-010':
            execution = executions[row['robot_ids'][0]]
            product = next(item for item in catalogue['products'] if item['sku'] == execution['inputs']['product_sku'])
            row['preconditions'] += ' The fixture customer is activated; the session basket is empty.'
            row['steps'] = '1. Log in using the documented account.\n2. Search and open Rose Nocturne.\n3. Enter the quantity shown in Input and leave the field.\n4. Attempt Add to cart when enabled; inspect validation and the basket.'
            expected = ('Basket quantity equals ' + execution['value'] + '; product total equals USD ' + str(Decimal(product['price']) * Decimal(execution['value'])) + '.'
                        if execution['expected'] == 'accepted' else
                        'Native quantity validation or a visible stock rejection prevents adding the product; the session basket stays empty.')
        else:
            row['preconditions'] += ' Journey registration requires its literal username and email to be unused; later checkpoints use that same activated customer and basket.'
            row['steps'] = {
                'DK':'1. Open Register.\n2. Enter the literal account details.\n3. Submit registration.\n4. Open the delivered activation link.\n5. Log out and log in again with the documented credentials.',
                'DN':'1. Open Log in after account activation.\n2. Enter the documented username and password.\n3. Submit and inspect the authenticated navigation.',
                'TK':'1. Open Search.\n2. Enter each literal search term shown in Input.\n3. Submit and inspect the matching product cards or empty result.',
                'SP':'1. Search for each documented product.\n2. Open the exact result.\n3. Inspect its name, price, size and description.\n4. Open and close the product image.',
                'GH':'1. Search and open each of the three products.\n2. Add one bottle of each.\n3. Open Cart and inspect all three lines and the subtotal.',
                'KM':'1. Open the prepared three-product basket.\n2. Perform the coupon action shown in Input.\n3. Inspect the displayed message, applied code and basket total.',
                'DC':'1. Open checkout addresses.\n2. Enter the documented billing and shipping details.\n3. Apply the copy/separate-address choice or empty-street condition.\n4. Continue and inspect the resulting fields or validation.',
                'VC':'1. Open delivery and payment methods.\n2. Select the documented carrier and Pay on delivery.\n3. Continue and inspect the selected methods and total.',
                'DH':'1. Open the prepared order confirmation.\n2. Set the terms checkbox to the documented state.\n3. Submit Place Order and inspect the outcome.',
                'LS':'1. Open My orders after placing the documented order.\n2. Open Details for that exact order.\n3. Inspect products, total, payment status and addresses.',
                'HT':'1. Register using the documented literal credentials and activate through delivered email.\n2. Log out and log in again.\n3. Search and inspect the three products; add one of each.\n4. Check coupon states and checkout addresses.\n5. Check each delivery quotation with Pay on delivery.\n6. Check the terms condition, place the order and reopen its exact history entry.'}[group]
            expected = {
                'DK':'The delivered activation link activates the account; the documented credentials authenticate successfully.',
                'DN':'The customer is authenticated and can access account navigation.',
                'TK':'Each product-name search returns its exact product; the absent term returns an empty result.',
                'SP':'All displayed details and loaded product images match the selected fixture products.',
                'GH':'The basket contains exactly three distinct product lines, one bottle each; subtotal is USD ' + str(subtotal) + '.',
                'KM':'Coupon state and arithmetic match the declared action.',
                'DC':'The documented address choice is retained; an empty required street produces a validation error.',
                'VC':'Selected carrier and Pay on delivery are retained; total equals discounted subtotal plus its configured fee.',
                'DH':'The terms condition determines whether confirmation is rejected or the COD order is received.',
                'LS':'The exact new order retains its lines, addresses and USD ' + str(total) + ' total; payment status is not paid.',
                'HT':'Registration, activation and login succeed; the three-product order is received for USD ' + str(total) + ' and its exact history entry remains not paid.'}[group]
        specific = {'TC-KM-001':'No coupon discount; subtotal remains USD ' + str(subtotal) + '.',
                    'TC-KM-002':'The unknown coupon is rejected with a visible message; no code is applied and subtotal remains USD ' + str(subtotal) + '.',
                    'TC-KM-003':'The coupon applies its configured percentage exactly once; discounted subtotal is USD ' + str(discounted) + '.',
                    'TC-KM-004':'The coupon is removed; subtotal returns to USD ' + str(subtotal) + '.',
                    'TC-DC-001':'Shipping fields copy the entered billing fields.',
                    'TC-DC-002':'The independent shipping address is retained separately from billing.',
                    'TC-DC-003':'The empty billing street has a native or server validation error; checkout stays at the address step.',
                    'TC-DH-001':'Confirmation is rejected while the terms checkbox is cleared; the order completion page is not reached.',
                    'TC-DH-002':'The order is received for USD ' + str(total) + '; its basket is emptied and payment remains not paid.'}
        if group == 'VC':
            selected = journey['carriers'][int(case_id[-3:]) - 1]
            expected = selected['service'] + ' and Pay on delivery are retained; delivery fee is USD ' + selected['fee'] + '; order total is USD ' + str(discounted + Decimal(selected['fee'])) + '.'
        row['expected'] = specific.get(case_id, expected)
        row.update(actual='Not executed',severity='Not assessed',priority='P1 - High',reproducibility='Not assessed',evidence='',reporter='',status='New')
        records.append(row)
    from scripts.customer_extensions import extension_records
    records.extend(extension_records(model, catalogue))
    return {'schema_version':1,'language':'en','model_sha256':semantic_hash(model),'headers':HEADERS,'cases':records,'case_count':len(records),'automation_count':len(plan['cases'])}


def execution_records(model, cases):
    """Select English business prose for each independent Robot execution."""
    from scripts.customer_design import build_plan, read_reference
    catalogue, store, partners = [read_reference(name) for name in ('catalogue','store','partners')]
    plan = build_plan(model,catalogue,store,partners)
    report = english_report(model,plan,catalogue)
    records = []
    for case in cases:
        row = next(row for row in report['cases'] if row['robot_ids']==[case['id']] and (case['stage']!='e2e' or row['id']=='TC-HT-001'))
        records.append(dict(row,id=case['id']))
    return records

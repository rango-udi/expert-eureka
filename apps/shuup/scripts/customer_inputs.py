"""Materialize literal public test inputs before preview or browser execution."""
import copy
import re


def validate_test_data(model):
    """Require explicit fictional identities and reject runtime interpolation tokens."""
    data = model.get('test_data', {})
    required = {'existing_customer', 'registration_baseline', 'journey_customer', 'absent_search', 'unknown_coupon', 'order_comment'}
    if set(data) != required:
        raise ValueError('Declare the complete literal customer test_data mapping.')
    for key in ('existing_customer', 'registration_baseline', 'journey_customer'):
        account = data[key]
        password_keys = ('password',) if key == 'existing_customer' else ('password1', 'password2')
        for field in ('username', 'email') + password_keys:
            value = account.get(field)
            if not isinstance(value, str) or not value or not value.isascii() or '$' in value or '<' in value or '>' in value:
                raise ValueError('Use a concrete ASCII test value for ' + key + '.' + field)
        if not account['email'].endswith('@fuzcake.test') or not re.fullmatch(r'[a-z][a-z0-9._]+', account['username']):
            raise ValueError('Use a fictional fuzcake.test account with a literal lowercase username.')
        if key != 'existing_customer' and account['password1'] != account['password2']:
            raise ValueError('Registration baselines require matching passwords.')
    if len({data[key]['username'] for key in ('existing_customer', 'registration_baseline', 'journey_customer')}) != 3:
        raise ValueError('Existing, rejected-registration and new-journey usernames must differ.')
    for key in required - {'existing_customer', 'registration_baseline', 'journey_customer'}:
        if not isinstance(data[key], str) or not data[key] or not data[key].isascii() or '$' in data[key]:
            raise ValueError('Use concrete English customer test data: ' + key)


def materialize_inputs(model, case, catalogue, store, partners):
    """Bind every typed value to the plan, including all public fixture passwords."""
    data = model['test_data']
    stage = case['stage']
    if stage == 'registration':
        inputs = copy.deepcopy(data['registration_baseline'])
        inputs[case['field']] = case['value']
        return inputs
    if stage == 'login':
        inputs = {key: data['existing_customer'][key] for key in ('username', 'password')}
        inputs[case['field']] = case['value']
        return inputs
    if stage == 'quantity':
        return {'account': {key: data['existing_customer'][key] for key in ('username', 'password')},
                'quantity': case['value'], 'product_sku': model['quantity_product']}
    products = {row['sku']: row for row in catalogue['products']}
    addresses = {row['id']: row for row in store['addresses']}
    return {'registration': {key: data['journey_customer'][key] for key in ('username', 'email', 'password1', 'password2')},
            'recipient': data['journey_customer']['full_name'], 'phone': store['phone'],
            'billing': copy.deepcopy(addresses[model['billing_address']]),
            'shipping': copy.deepcopy(addresses[model['shipping_address']]),
            'products': [dict(products[sku], quantity='1') for sku in model['order_products']],
            'carriers': copy.deepcopy(partners['carriers']), 'final_carrier': model['final_carrier'],
            'coupon': copy.deepcopy(store['welcome_offer']), 'unknown_coupon': data['unknown_coupon'],
            'absent_search': data['absent_search'], 'payment': 'Pay on delivery', 'order_comment': data['order_comment']}

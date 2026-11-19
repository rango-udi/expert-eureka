"""Bind additional customer scenarios to literal inputs and bilingual report records."""
import copy
import json
from decimal import Decimal
from pathlib import Path
import re

APP = Path(__file__).resolve().parents[1]
STAGES = {'B': 'basket_update', 'A': 'address_book', 'P': 'password_change'}
GROUPS = {'basket_update': ('Basket changes', 'Thay \u0111\u1ed5i gi\u1ecf h\u00e0ng'),
          'address_book': ('Address book', 'S\u1ed5 \u0111\u1ecba ch\u1ec9'),
          'password_change': ('Password change', '\u0110\u1ed5i m\u1eadt kh\u1ea9u')}


def definitions():
    """Read display prose without putting translation into frozen execution payloads."""
    return json.loads((APP / 'tests/data/CUSTOMER_EXTENSION_TEXT.json').read_text())['cases']


def extension_cases(model):
    """Validate explicit extension operations and their exact input dictionaries."""
    rows = copy.deepcopy(model.get('extensions', {}).get('cases', []))
    if not rows:
        return []
    prose = {row['robot_ids'][0]: row for row in definitions()}
    if {row['id'] for row in rows} != set(prose):
        raise ValueError('Declare every reviewed extension execution exactly once.')
    accounts = model['extensions']['accounts']
    for account in accounts:
        _validate_literals(account)
    if len({row['username'] for row in accounts}) != len(accounts) or len({row['email'] for row in accounts}) != len(accounts):
        raise ValueError('Dedicated extension accounts must have distinct names and emails.')
    domains = model['extensions']['domains']
    if domains['basket_quantity'] != {key: model['quantity_model']['fields']['quantity'][key] for key in ('min','max','step','nominal')}:
        raise ValueError('Basket extension bounds must match the reviewed quantity domain.')
    if domains['address_title_length'] != {'min':'1','max':'255','step':'1','nominal':'13'}:
        raise ValueError('Address-title boundaries must match the pinned native required/max-length rule.')
    operations = {'basket_update': {'update', 'delete_one', 'delete_last', 'repeat_add'},
                  'address_book': {'create', 'edit', 'delete', 'ownership'}, 'password_change': {'change'}}
    for row in rows:
        if not re.fullmatch(r'SH-CUST-[BAP][0-9]{2}', row['id']) or row['stage'] != STAGES[row['id'][8]]:
            raise ValueError('Extension execution ID and stage disagree.')
        if row['operation'] not in operations[row['stage']] or row['id'] not in prose:
            raise ValueError('Declare executable extension operations and their readable prose.')
        expected = {'basket_update': {'accepted', 'rejected', 'unchanged'},
                    'address_book': {'accepted', 'rejected', 'bounded'},
                    'password_change': {'accepted', 'rejected', 'login_required'}}
        if row['expected'] not in expected[row['stage']]:
            raise ValueError('Unsupported extension outcome.')
        definition = prose[row['id']]
        if row['business_id'] != definition['id'] or row['covers'] != definition['analysis'].split(', '):
            raise ValueError('Extension business IDs and analysis must match their definitions.')
        if not row['covers'] or not isinstance(row['inputs'], dict):
            raise ValueError('Extension cases require literal inputs and real analysis obligations.')
        row['title'], row['description'] = definition['en']['title'], definition['en']['description']
        _validate_literals(row['inputs'])
        inputs = row['inputs']
        if row['stage'] != 'basket_update' and inputs['account'] not in accounts:
            raise ValueError('Extension account values must match a declared dedicated fixture.')
        if row['stage'] == 'basket_update' and row['operation'] == 'update':
            value = inputs['value']
            outcome = 'unchanged' if value == '' else 'accepted' if value in ('1','2','3','24','25') else 'rejected'
            if row['expected'] != outcome:
                raise ValueError('Basket expected outcomes must preserve the reviewed quantity oracle.')
        if row['stage'] == 'address_book':
            outcome = 'rejected' if not inputs['title'] or not inputs['address']['street'] else 'bounded' if len(inputs['title']) > 255 else 'accepted'
            if row['expected'] != outcome or inputs['role'] != '1' or inputs['status'] != '1':
                raise ValueError('Address expected outcomes and native shipping/enabled options disagree.')
        if row['stage'] == 'password_change':
            expected = 'login_required' if row['id'] == 'SH-CUST-P07' else 'accepted' if row['id'] == 'SH-CUST-P06' else 'rejected'
            if row['expected'] != expected:
                raise ValueError('Password outcomes must match the reviewed authentication rules.')
        if row['stage'] == 'basket_update':
            account = model['test_data']['existing_customer']
            if inputs['account'] != {key: account[key] for key in ('username','password')}:
                raise ValueError('Basket extensions must use the reviewed existing customer credentials.')
            if inputs['product_sku'] != model['quantity_product']:
                raise ValueError('Basket extensions must use the independently stocked boundary product.')
    if len({row['id'] for row in rows}) != len(rows):
        raise ValueError('Extension IDs must be unique.')
    by_id = {row['id']: row for row in rows}
    if [by_id['SH-CUST-B'+str(i).zfill(2)]['inputs']['value'] for i in range(1,10)] != ['0','1','2','24','25','26','3','','1.5']:
        raise ValueError('Review the executable basket BVA/EP vectors before changing them.')
    title_cases = [4,6,7,8,9,10,1]
    if [len(by_id['SH-CUST-A'+str(i).zfill(2)]['inputs']['title']) for i in title_cases] != [0,1,2,254,255,256,13]:
        raise ValueError('Review all concrete address-title BVA representatives together.')
    return rows


def _validate_literals(value):
    """Refuse unresolved tokens and non-English literal input values before generation."""
    if isinstance(value, dict):
        for item in value.values():
            _validate_literals(item)
    elif not isinstance(value, str) or not value.isascii() or any(token in value for token in ('${', '%{', '{{', '<', '>')):
        raise ValueError('Extension input values must be concrete English strings.')


def literal_text(inputs, language):
    """Flatten input fields into readable labels and exact values, never source expressions."""
    labels = {'account': 'T\u00e0i kho\u1ea3n', 'other_account': 'T\u00e0i kho\u1ea3n kh\u00e1c',
              'username': 'T\u00ean \u0111\u0103ng nh\u1eadp', 'password': 'M\u1eadt kh\u1ea9u',
              'first_name': 'T\u00ean', 'last_name': 'H\u1ecd', 'email': 'Email', 'address': '\u0110\u1ecba ch\u1ec9',
              'role': 'Lo\u1ea1i (1 = shipping)', 'status': 'Tr\u1ea1ng th\u00e1i (1 = enabled)', 'name': 'Ng\u01b0\u1eddi nh\u1eadn', 'street': '\u0110\u01b0\u1eddng', 'street2': '\u0110\u01b0\u1eddng b\u1ed5 sung',
              'city': 'Th\u00e0nh ph\u1ed1', 'postal_code': 'M\u00e3 b\u01b0u ch\u00ednh', 'country': 'Qu\u1ed1c gia',
              'phone': '\u0110i\u1ec7n tho\u1ea1i', 'title': 'Ti\u00eau \u0111\u1ec1', 'updated_street': '\u0110\u01b0\u1eddng sau s\u1eeda',
              'product_sku': 'SKU', 'second_sku': 'SKU th\u1ee9 hai', 'initial_quantity': 'S\u1ed1 l\u01b0\u1ee3ng ban \u0111\u1ea7u',
              'second_quantity': 'S\u1ed1 l\u01b0\u1ee3ng th\u1ee9 hai', 'value': 'S\u1ed1 l\u01b0\u1ee3ng nh\u1eadp',
              'old_password': 'M\u1eadt kh\u1ea9u hi\u1ec7n t\u1ea1i', 'new_password': 'M\u1eadt kh\u1ea9u m\u1edbi',
              'confirm_password': 'X\u00e1c nh\u1eadn m\u1eadt kh\u1ea9u'}
    rows = []
    for key, value in inputs.items():
        label = labels[key] if language == 'vi' else key.replace('_', ' ').capitalize()
        if isinstance(value, dict):
            rows.append(label + ':')
            rows.append(literal_text(value, language))
        else:
            rows.append(label + ': ' + (value if value else ('\u0110\u1ec3 tr\u1ed1ng' if language == 'vi' else 'Empty')))
    return '\n'.join(rows)


def extension_records(model, catalogue, language='en'):
    """Project the same frozen input values into manual and execution presentations."""
    cases = {row['id']: row for row in extension_cases(model)}
    records = []
    for definition in definitions():
        if definition['robot_ids'][0] not in cases:
            continue
        case = cases[definition['robot_ids'][0]]
        row = {key: copy.deepcopy(definition[key]) for key in ('id', 'robot_ids', 'requirement', 'analysis')}
        row.update(copy.deepcopy(definition[language]))
        row['module'] = GROUPS[case['stage']][language == 'vi']
        row['preconditions'] = ('Dedicated reviewed accounts are active; original password matches the input; a fresh session and initial fixture stock are required. No address with this test title exists.' if language == 'en' else
                                'T\u00e0i kho\u1ea3n ki\u1ec3m th\u1eed \u0111\u00e3 k\u00edch ho\u1ea1t, m\u1eadt kh\u1ea9u ban \u0111\u1ea7u kh\u1edbp d\u1eef li\u1ec7u; phi\u00ean m\u1edbi, t\u1ed3n kho fixture ban \u0111\u1ea7u. Ch\u01b0a c\u00f3 \u0111\u1ecba ch\u1ec9 mang ti\u00eau \u0111\u1ec1 ca n\u00e0y.')
        row['input'] = literal_text(case['inputs'], language)
        if case['stage'] == 'basket_update':
            products = {p['sku']: p for p in catalogue['products']}
            price = Decimal(products[case['inputs']['product_sku']]['price'])
            quantity = case['inputs'].get('value', '2') if case['expected'] == 'accepted' else '2'
            amount = price * (Decimal('3') if case['operation'] == 'repeat_add' else Decimal(quantity or '2'))
            if case['operation'] == 'delete_one':
                amount = Decimal(products[case['inputs']['second_sku']]['price'])
            if case['operation'] == 'delete_last':
                amount = Decimal('0')
            row['expected'] += ('\nSaved basket total: ' if language == 'en' else '\nT\u1ed5ng ti\u1ec1n gi\u1ecf \u0111\u00e3 l\u01b0u: ') + str(amount.quantize(Decimal('0.01'))) + ' USD.'
        row.update(actual='Not executed' if language == 'en' else 'Ch\u01b0a th\u1ef1c hi\u1ec7n',
                   severity='Not assessed' if language == 'en' else 'Ch\u01b0a \u0111\u00e1nh gi\u00e1',
                   priority='P1 - High' if language == 'en' else 'P1 - Cao',
                   reproducibility='Not assessed' if language == 'en' else 'Ch\u01b0a \u0111\u00e1nh gi\u00e1',
                   evidence='', reporter='', status='New' if language == 'en' else 'M\u1edbi (new)')
        records.append(row)
    return records


def extend_analysis(data, model):
    """Add concrete boundary rows, partition definitions and witnessed decision rules."""
    cases = extension_cases(model)
    data['extra_bva_headers'] = ['M\u00e3 bi\u00ean', 'Tr\u01b0\u1eddng / ng\u1eef c\u1ea3nh', 'Gi\u00e1 tr\u1ecb / \u0111\u1ed9 d\u00e0i', 'K\u1ef3 v\u1ecdng', 'Ca li\u00ean quan']
    data['extra_bva'] = []
    partitions = {}
    for case in cases:
        identifier = case['business_id']
        definition = next(row for row in definitions() if row['id'] == identifier)
        for obligation in case['covers']:
            if obligation.startswith('BVA-'):
                value = case['inputs'].get('value') if case['stage'] == 'basket_update' else len(case['inputs']['title'])
                data['extra_bva'].append([obligation, GROUPS[case['stage']][1], int(value) if isinstance(value, str) else value,
                                          definition['vi']['expected'], identifier])
            if obligation.startswith('EP-'):
                field = 'S\u1ed1 l\u01b0\u1ee3ng' if case['stage'] == 'basket_update' else 'Ti\u00eau \u0111\u1ec1 / \u0111\u1ecba ch\u1ec9' if case['stage'] == 'address_book' else 'M\u1eadt kh\u1ea9u / phi\u00ean'
                value = case['inputs'].get('value', case['inputs'].get('title', case['inputs'].get('old_password', '')))
                if obligation == 'EP-SD-05':
                    value = case['inputs']['address']['street']
                if obligation == 'EP-SD-04':
                    value = case['inputs']['other_account']['username']
                if case['stage'] == 'password_change' and case['expected'] != 'login_required':
                    value = case['inputs']['old_password'] + ' / ' + case['inputs']['new_password'] + ' / ' + case['inputs']['confirm_password']
                if case['expected'] == 'login_required':
                    value = 'Signed out'
                valid = case['expected'] == 'accepted' and obligation != 'EP-SD-04'
                if obligation not in partitions:
                    partitions[obligation] = [obligation, GROUPS[case['stage']][1], field, definition['vi']['title'],
                                              value or '\u0110\u1ec3 tr\u1ed1ng', data['valid_partition'] if valid else data['invalid_partition'], identifier]
                else:
                    partitions[obligation][-1] += ', ' + identifier
    labels = {"EP-GB-01": "S\u1ed1 nguy\u00ean trong kho\u1ea3ng 1 \u0111\u1ebfn 25", "EP-GB-02": "S\u1ed1 nguy\u00ean nh\u1ecf h\u01a1n t\u1ed1i thi\u1ec3u 1", "EP-GB-03": "S\u1ed1 nguy\u00ean l\u1edbn h\u01a1n t\u1ed3n kho 25", "EP-GB-08": "\u00d4 c\u1eadp nh\u1eadt tr\u1ed1ng, gi\u1eef s\u1ed1 \u0111\u00e3 l\u01b0u", "EP-GB-09": "S\u1ed1 th\u1eadp ph\u00e2n cho \u0111\u01a1n v\u1ecb chai nguy\u00ean", "EP-SD-01": "Ti\u00eau \u0111\u1ec1 d\u00e0i t\u1eeb 1 \u0111\u1ebfn 255 k\u00fd t\u1ef1 v\u00e0 \u0111\u1ecba ch\u1ec9 \u0111\u1ea7y \u0111\u1ee7", "EP-SD-02": "Ti\u00eau \u0111\u1ec1 tr\u1ed1ng", "EP-SD-03": "Thao t\u00e1c nh\u1eadp ti\u00eau \u0111\u1ec1 v\u01b0\u1ee3t 255 k\u00fd t\u1ef1", "EP-SD-04": "T\u00e0i nguy\u00ean \u0111\u1ecba ch\u1ec9 thu\u1ed9c kh\u00e1ch kh\u00e1c", "EP-SD-05": "\u0110\u01b0\u1eddng \u0111\u1ec3 tr\u1ed1ng", "EP-MK-01": "M\u1eadt kh\u1ea9u hi\u1ec7n t\u1ea1i sai", "EP-MK-02": "M\u1eadt kh\u1ea9u hi\u1ec7n t\u1ea1i tr\u1ed1ng", "EP-MK-03": "M\u1eadt kh\u1ea9u m\u1edbi tr\u1ed1ng", "EP-MK-04": "X\u00e1c nh\u1eadn m\u1eadt kh\u1ea9u m\u1edbi tr\u1ed1ng", "EP-MK-05": "Hai m\u1eadt kh\u1ea9u m\u1edbi kh\u00e1c nhau", "EP-MK-06": "M\u1eadt kh\u1ea9u hi\u1ec7n t\u1ea1i \u0111\u00fang, hai m\u1eadt kh\u1ea9u m\u1edbi tr\u00f9ng nhau", "EP-MK-07": "Phi\u00ean ch\u01b0a \u0111\u0103ng nh\u1eadp"}
    for identifier, row in partitions.items():
        row[3] = labels[identifier]
    data['ep'].extend(partitions.values())
    tables = [
        ('Thao t\u00e1c gi\u1ecf h\u00e0ng', ['QD-GB-01','QD-GB-02','QD-GB-03'],
         [['C\u00f2n s\u1ea3n ph\u1ea9m kh\u00e1c', 'T','F','F'],['Thao t\u00e1c x\u00f3a d\u00f2ng','T','T','F'],['Th\u00eam l\u1eb7p c\u00f9ng SKU','F','F','T']],
         [['Gi\u1eef s\u1ea3n ph\u1ea9m kh\u00e1c','X','-','-'],['Gi\u1ecf tr\u1ed1ng','-','X','-'],['G\u1ed9p s\u1ed1 l\u01b0\u1ee3ng','-','-','X']]),
        ('Ch\u1ee7 s\u1edf h\u1eefu s\u1ed5 \u0111\u1ecba ch\u1ec9', ['QD-SD-01','QD-SD-02','QD-SD-03'],
         [['\u0110\u00fang ch\u1ee7 \u0111\u1ecba ch\u1ec9','T','T','F'],['S\u1eeda \u0111\u1ecba ch\u1ec9','T','F','-'],['X\u00f3a \u0111\u1ecba ch\u1ec9','F','T','T']],
         [['L\u01b0u \u0111\u01b0\u1eddng m\u1edbi','X','-','-'],['X\u00f3a \u0111\u1ecba ch\u1ec9 c\u1ee7a m\u00ecnh','-','X','-'],['Gi\u1eef nguy\u00ean \u0111\u1ecba ch\u1ec9 ng\u01b0\u1eddi kh\u00e1c','-','-','X']]),
        ('\u0110\u1ed5i m\u1eadt kh\u1ea9u', ['QD-MK-'+str(i).zfill(2) for i in range(1,8)],
         [['\u0110\u00e3 \u0111\u0103ng nh\u1eadp','T','T','T','T','T','T','F'],['M\u1eadt kh\u1ea9u hi\u1ec7n t\u1ea1i \u0111\u00fang','F','F','T','T','T','T','-'],['M\u1eadt kh\u1ea9u m\u1edbi \u0111\u1ea7y \u0111\u1ee7, kh\u1edbp nhau','T','T','F','F','F','T','-']],
         [['Gi\u1eef m\u1eadt kh\u1ea9u c\u0169','X','X','X','X','X','-','X'],['\u0110\u1ed5i v\u00e0 ph\u1ee5c h\u1ed3i qua UI','-','-','-','-','-','X','-'],['Chuy\u1ec3n t\u1edbi \u0111\u0103ng nh\u1eadp','-','-','-','-','-','-','X']])]
    for title, rules, conditions, actions in tables:
        data['decisions'].append({'title':title,'rules':rules,'conditions':conditions,'actions':actions,
                                  'case_ids':[', '.join(case['business_id'] for case in cases if rule in case['covers']) for rule in rules]})
    data['requirements'].update({'YC-GB':'C\u1eadp nh\u1eadt v\u00e0 x\u00f3a gi\u1ecf h\u00e0ng',
                                 'YC-SD':'Qu\u1ea3n l\u00fd s\u1ed5 \u0111\u1ecba ch\u1ec9', 'YC-MK':'\u0110\u1ed5i m\u1eadt kh\u1ea9u'})
    data['guide'].append(['Ca m\u1edf r\u1ed9ng', '30 ca \u0111\u1ed9c l\u1eadp: 12 gi\u1ecf, 11 s\u1ed5 \u0111\u1ecba ch\u1ec9, 7 m\u1eadt kh\u1ea9u. Grace Mitchell v\u00e0 Henry Foster l\u00e0 t\u00e0i kho\u1ea3n fixture ri\u00eang. \u0110\u1ecba ch\u1ec9 v\u1eeba t\u1ea1o \u0111\u01b0\u1ee3c x\u00f3a sau ki\u1ec3m tra; m\u1eadt kh\u1ea9u \u0111\u01b0\u1ee3c ph\u1ee5c h\u1ed3i qua UI. N\u1ebfu b\u1ecb ng\u1eaft, \u0111\u1ed1i chi\u1ebfu evidence v\u00e0 d\u1eef li\u1ec7u tr\u01b0\u1edbc khi ch\u1ea1y l\u1ea1i; seed kh\u00f4ng reset m\u1eadt kh\u1ea9u.'])

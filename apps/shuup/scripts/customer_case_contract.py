"""Render concrete customer inputs as Vietnamese manual steps, without code or tokens."""


def display(value):
    """Represent an intentionally empty control in natural language."""
    return value if value != '' else '\u0110\u1ec3 tr\u1ed1ng'


def account_text(inputs, registration=False):
    """Show every actual username, email and test password as a literal value."""
    fields = [('T\u00ean \u0111\u0103ng nh\u1eadp', 'username'), ('Email', 'email'), ('M\u1eadt kh\u1ea9u', 'password1'),
              ('Nh\u1eadp l\u1ea1i m\u1eadt kh\u1ea9u', 'password2')] if registration else [('T\u00ean \u0111\u0103ng nh\u1eadp', 'username'), ('M\u1eadt kh\u1ea9u', 'password')]
    return '\n'.join(label + ': ' + display(inputs[key]) for label, key in fields)


def address_text(inputs, kind, same=False, missing=False):
    """Describe the exact recipient and address used at a checkout checkpoint."""
    address = inputs[kind]
    return '\n'.join(['Ng\u01b0\u1eddi nh\u1eadn: ' + inputs['recipient'], '\u0110i\u1ec7n tho\u1ea1i: ' + inputs['phone'],
                      'Email: ' + inputs['registration']['email'],
                      '\u0110\u01b0\u1eddng: ' + ('\u0110\u1ec3 tr\u1ed1ng' if missing else address['street']),
                      '\u0110\u1ecba ch\u1ec9 b\u1ed5 sung: ' + address.get('street2', ''), 'Th\u00e0nh ph\u1ed1: ' + address['city'],
                      'M\u00e3 b\u01b0u ch\u00ednh: ' + address['postal_code'], 'Qu\u1ed1c gia: United States of America',
                      'V\u00f9ng: kh\u00f4ng ch\u1ecdn', 'Giao \u0111\u1ebfn \u0111\u1ecba ch\u1ec9 thanh to\u00e1n: ' + ('C\u00f3' if same else 'Kh\u00f4ng')])


def product_text(inputs):
    """Use actual fixture products and concrete one-bottle quantities."""
    return '\n'.join(row['name'] + ': ' + row['price'] + ' USD; ' + row['size'] + '; 1 chai' for row in inputs['products'])


def business_input(case_id, executions, catalogue):
    """Project literal execution data into each existing Vietnamese business scenario."""
    journey = executions['SH-CUST-E01']['inputs']
    if case_id.startswith('TC-DK-'):
        index = int(case_id[-3:])
        inputs = journey['registration'] if index == 1 else executions['SH-CUST-R' + str(index - 1).zfill(2)]['inputs']
        return account_text(inputs, True)
    if case_id.startswith('TC-DN-'):
        index = int(case_id[-3:])
        inputs = {'username': journey['registration']['username'], 'password': journey['registration']['password1']} if index == 1 else executions['SH-CUST-L' + str(index - 1).zfill(2)]['inputs']
        return account_text(inputs)
    if case_id.startswith('TC-GH-') and case_id != 'TC-GH-010':
        case = executions['SH-CUST-Q' + case_id[-2:]]
        product = next(row for row in catalogue['products'] if row['sku'] == case['inputs']['product_sku'])
        return account_text(case['inputs']['account']) + '\nS\u1ea3n ph\u1ea9m: ' + product['name'] + '\n\u0110\u01a1n gi\u00e1: ' + product['price'] + ' USD/chai\nC\u00f2n b\u00e1n: ' + str(product['stock']) + ' chai\nS\u1ed1 l\u01b0\u1ee3ng nh\u1eadp: ' + display(case['inputs']['quantity'])
    if case_id == 'TC-TK-001':
        return '\n'.join('L\u1ea7n ' + str(index) + ': ' + row['name'] for index, row in enumerate(journey['products'], 1))
    if case_id == 'TC-TK-002':
        return 'T\u1eeb kh\u00f3a: ' + journey['absent_search']
    if case_id == 'TC-SP-001':
        return '\n'.join(row['name'] + ': ' + row['price'] + ' USD; ' + row['size'] + '\nM\u00f4 t\u1ea3: ' + row['description'] for row in journey['products'])
    if case_id == 'TC-GH-010':
        return product_text(journey) + '\nKh\u00f4ng nh\u1eadp m\u00e3 gi\u1ea3m gi\u00e1.'
    if case_id.startswith('TC-KM-'):
        return {'001':'Kh\u00f4ng nh\u1eadp m\u00e3 gi\u1ea3m gi\u00e1.', '002':'M\u00e3 gi\u1ea3m gi\u00e1: ' + journey['unknown_coupon'],
                '003':'M\u00e3 gi\u1ea3m gi\u00e1: ' + journey['coupon']['code'] + '\nM\u1ee9c gi\u1ea3m: 10% ti\u1ec1n h\u00e0ng',
                '004':'X\u00f3a m\u00e3 gi\u1ea3m gi\u00e1 \u0111\u00e3 \u00e1p d\u1ee5ng: ' + journey['coupon']['code']}[case_id[-3:]]
    if case_id.startswith('TC-DC-'):
        if case_id.endswith('001'):
            return address_text(journey, 'billing', same=True)
        if case_id.endswith('003'):
            return address_text(journey, 'billing', missing=True)
        return 'Ng\u01b0\u1eddi nh\u1eadn: ' + journey['recipient'] + '; ' + journey['phone'] + '\nEmail: ' + journey['registration']['email'] + '\nThanh to\u00e1n: ' + ', '.join(journey['billing'][key] for key in ('street','street2','city','postal_code')) + '\nGiao h\u00e0ng: ' + ', '.join(journey['shipping'][key] for key in ('street','street2','city','postal_code')) + '\nQu\u1ed1c gia c\u1ea3 hai \u0111\u1ecba ch\u1ec9: United States of America\nV\u00f9ng: kh\u00f4ng ch\u1ecdn\nGiao \u0111\u1ebfn \u0111\u1ecba ch\u1ec9 thanh to\u00e1n: Kh\u00f4ng'
    if case_id.startswith('TC-VC-'):
        carrier = journey['carriers'][int(case_id[-3:]) - 1]
        return 'Giao h\u00e0ng: ' + carrier['name'] + ' - ' + carrier['service'] + '\nPh\u00ed giao h\u00e0ng: ' + carrier['fee'] + ' USD\nThanh to\u00e1n: ' + journey['payment'] + '\nTi\u1ec1n sau gi\u1ea3m gi\u00e1: 271.80 USD'
    if case_id == 'TC-DH-001':
        return '\u0110\u1ed3ng \u00fd \u0111i\u1ec1u kho\u1ea3n: Kh\u00f4ng'
    if case_id == 'TC-DH-002':
        return product_text(journey) + '\nM\u00e3 gi\u1ea3m gi\u00e1: ' + journey['coupon']['code'] + '\nGiao h\u00e0ng: Careful delivery\nThanh to\u00e1n: Pay on delivery\n\u0110\u1ed3ng \u00fd \u0111i\u1ec1u kho\u1ea3n: C\u00f3\nGhi ch\u00fa: ' + journey['order_comment']
    if case_id == 'TC-LS-001':
        return 'Ch\u1ecdn \u0111\u01a1n v\u1eeba \u0111\u1eb7t c\u1ee7a ' + journey['registration']['username'] + '\nT\u1ed5ng ti\u1ec1n: 276.75 USD\nThanh to\u00e1n: Pay on delivery; ch\u01b0a thanh to\u00e1n\nThanh to\u00e1n: ' + journey['billing']['street'] + '\nGiao h\u00e0ng: ' + journey['shipping']['street']
    if case_id == 'TC-HT-001':
        return account_text(journey['registration'], True) + '\n' + product_text(journey) + '\nNg\u01b0\u1eddi nh\u1eadn: ' + journey['recipient'] + '; ' + journey['phone'] + '\nThanh to\u00e1n: ' + journey['billing']['street'] + ', ' + journey['billing']['city'] + ', ' + journey['billing']['postal_code'] + '\nGiao h\u00e0ng: ' + journey['shipping']['street'] + ', ' + journey['shipping']['city'] + ', ' + journey['shipping']['postal_code'] + '\nQu\u1ed1c gia: United States of America; v\u00f9ng: kh\u00f4ng ch\u1ecdn\nM\u00e3 gi\u1ea3m gi\u00e1: ' + journey['coupon']['code'] + '\nGiao h\u00e0ng: Careful delivery; thanh to\u00e1n: Pay on delivery\n\u0110\u1ed3ng \u00fd \u0111i\u1ec1u kho\u1ea3n: C\u00f3\nGhi ch\u00fa: ' + journey['order_comment']
    raise ValueError('Add an explicit literal input projection for business case ' + case_id)


def prepare_business_cases(prose, executions, catalogue):
    """Keep the authored scenario scope while binding its input values to Robot data."""
    import copy
    rows = copy.deepcopy(prose['cases'])
    journey = executions['SH-CUST-E01']['inputs']
    existing = executions['SH-CUST-Q01']['inputs']['account']
    baseline = executions['SH-CUST-R01']['inputs']
    unknown = executions['SH-CUST-L02']['inputs']['username']
    replacements = {'emily.carter@fuzcake.test': journey['registration']['email'],
                    'emily.carter': journey['registration']['username'],
                    'Emily!4826Cedar': journey['registration']['password1'],
                    'Emily Carter': journey['recipient'],
                    'lucas.parker@fuzcake.test': baseline['email']}
    for row in rows:
        for key in ('description','preconditions','steps','expected'):
            for old, new in replacements.items():
                row[key] = row[key].replace(old, new)
    for row in rows:
        row['input'] = business_input(row['id'], executions, catalogue)
        if row['id'].startswith('TC-DK-') and row['id'] != 'TC-DK-001':
            execution = executions[row['robot_ids'][0]]
            row['preconditions'] = 'Kh\u00e1ch ch\u01b0a \u0111\u0103ng nh\u1eadp. T\u00ean lucas.parker v\u00e0 email lucas.parker@fuzcake.test ch\u01b0a \u0111\u01b0\u1ee3c \u0111\u0103ng k\u00fd. T\u00e0i kho\u1ea3n oliver.bennett \u0111\u00e3 t\u1ed3n t\u1ea1i v\u00e0 \u0111\u01b0\u1ee3c k\u00edch ho\u1ea1t.'
            row['steps'] = '1. Ch\u1ecdn Log in, sau \u0111\u00f3 ch\u1ecdn Register.\n2. Nh\u1eadp \u0111\u00fang b\u1ed1n gi\u00e1 tr\u1ecb c\u1ee5 th\u1ec3 trong c\u1ed9t d\u1eef li\u1ec7u.\n3. Nh\u1ea5n Register.\n4. Ki\u1ec3m tra l\u1ed7i t\u1ea1i tr\u01b0\u1eddng \u0111ang th\u1eed v\u00e0 x\u00e1c nh\u1eadn kh\u00e1ch ch\u01b0a \u0111\u0103ng nh\u1eadp.'
        if row['id'].startswith('TC-DN-') and row['id'] != 'TC-DN-001':
            row['preconditions'] = 'T\u00e0i kho\u1ea3n oliver.bennett \u0111\u00e3 \u0111\u01b0\u1ee3c k\u00edch ho\u1ea1t, m\u1eadt kh\u1ea9u Oliver!4826Maple. T\u00ean nathan.reed ch\u01b0a t\u1ed3n t\u1ea1i. Kh\u00e1ch \u0111ang \u0111\u0103ng xu\u1ea5t.'
            row['steps'] = '1. M\u1edf Log in.\n2. Nh\u1eadp \u0111\u00fang t\u00ean \u0111\u0103ng nh\u1eadp v\u00e0 m\u1eadt kh\u1ea9u trong c\u1ed9t d\u1eef li\u1ec7u.\n3. Nh\u1ea5n Log in.\n4. Ki\u1ec3m tra th\u00f4ng b\u00e1o t\u1eeb ch\u1ed1i v\u00e0 x\u00e1c nh\u1eadn kh\u00e1ch v\u1eabn ch\u01b0a \u0111\u0103ng nh\u1eadp.'
        if row['id'].startswith('TC-GH-') and row['id'] != 'TC-GH-010':
            row['preconditions'] = 'T\u00e0i kho\u1ea3n oliver.bennett \u0111\u00e3 k\u00edch ho\u1ea1t; m\u1eadt kh\u1ea9u Oliver!4826Maple. Gi\u1ecf c\u1ee7a phi\u00ean tr\u1ed1ng. Rose Nocturne c\u00f2n 25 chai; gi\u00e1 89.00 USD/chai.'
        if row['id'] == 'TC-DC-003':
            row['preconditions'] = 'Emily Carter \u0111\u00e3 \u0111\u0103ng nh\u1eadp; ba s\u1ea3n ph\u1ea9m v\u00e0 m\u00e3 gi\u1ea3m gi\u00e1 \u0111\u00e3 \u1edf trong gi\u1ecf. Hai \u0111\u1ecba ch\u1ec9 \u0111\u00e3 \u0111\u01b0\u1ee3c nh\u1eadp \u0111\u1ea7y \u0111\u1ee7 nh\u01b0 ca giao \u0111\u1ebfn \u0111\u1ecba ch\u1ec9 ri\u00eang.'
            row['steps'] = '1. Gi\u1eef l\u1ef1a ch\u1ecdn giao \u0111\u1ebfn \u0111\u1ecba ch\u1ec9 ri\u00eang.\n2. X\u00f3a ri\u00eang \u00f4 \u0111\u01b0\u1eddng c\u1ee7a \u0111\u1ecba ch\u1ec9 thanh to\u00e1n, gi\u1eef h\u1ee3p l\u1ec7 c\u00e1c \u00f4 kh\u00e1c.\n3. Nh\u1ea5n Continue.\n4. Ki\u1ec3m tra l\u1ed7i thi\u1ebfu \u0111\u01b0\u1eddng v\u00e0 x\u00e1c nh\u1eadn ch\u01b0a sang b\u01b0\u1edbc ch\u1ecdn giao h\u00e0ng.'
    for row in rows:
        for key in ('preconditions', 'steps', 'expected'):
            row[key] = row[key].replace('oliver.bennett', existing['username']).replace('Oliver!4826Maple', existing['password']).replace('nathan.reed', unknown)
            row[key] = row[key].replace('lucas.parker@fuzcake.test', baseline['email']).replace('lucas.parker', executions['SH-CUST-R04']['inputs']['username'])
    return rows


def case_records(model, cases):
    """Render English execution records; Vietnamese prose is reserved for Excel."""
    from scripts.customer_english_cases import execution_records
    return execution_records(model, cases)

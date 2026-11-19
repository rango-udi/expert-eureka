"""Customer-only Browser keywords with UI assertions and a local-mail inbox adapter.

There are no application imports, SQL, HTTP clients or hidden basket mutations.
Read-only DOM inspection observes values/validity. The only filesystem input
beyond fixture specifications is the customer's delivered activation email.
"""
import base64
from decimal import Decimal
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses
from html import unescape
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlsplit
from robot.libraries.BuiltIn import BuiltIn
from robot.api.deco import keyword
from test_design.specification import semantic_hash
import sys
APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
from scripts.customer_evidence import EvidenceRun
from tests.robot.CustomerExtensions import CustomerExtensionKeywords


class CustomerJourney(CustomerExtensionKeywords):
    """Translate one stage-specific design case into visible customer interactions."""

    ROBOT_LIBRARY_SCOPE = 'SUITE'
    ROBOT_AUTO_KEYWORDS = False

    def __init__(self, model_path):
        """Read the frozen test specification and original shared fixture oracles."""
        self.model = json.loads(Path(model_path).read_text())
        reference = Path('/fuzcake-data/records')
        self.catalogue = {p['sku']: p for p in json.loads((reference / 'catalogue.json').read_text())['products']}
        self.store = json.loads((reference / 'store.json').read_text())
        self.carriers = json.loads((reference / 'partners.json').read_text())['carriers']
        provenance = self.model.get('_provenance', {})
        source = {key: value for key, value in self.model.items() if key != '_provenance'}
        if semantic_hash(source) != provenance.get('model_sha256'):
            raise ValueError('Frozen customer model changed; regenerate the suite.')
        references = {'catalogue': json.loads((reference / 'catalogue.json').read_text()), 'store': self.store,
                      'partners': json.loads((reference / 'partners.json').read_text())}
        if {name: semantic_hash(value) for name, value in references.items()} != provenance.get('reference_sha256'):
            raise ValueError('Shared fixture specification changed; regenerate the customer suite.')
        self.base = os.environ['BASE_URL'].rstrip('/')
        self.robot = None
        self.browser = None
        self.evidence = None
        self.active_business_cases = []
        self.active_robot_id = None

    def _kw(self, name, *arguments):
        """Run a Browser keyword through Robot so actions remain visible in log.html."""
        return self.robot.run_keyword('Browser.' + name, *arguments)

    def _until(self, probe, description):
        """Poll an observable UI state with a deadline, never treat elapsed time as success."""
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if probe():
                return
            time.sleep(0.15)
        raise AssertionError('Timed out waiting for ' + description)

    def _read(self, selector, script):
        """Inspect the actual DOM without changing attributes, options, forms or storage."""
        return self._kw('Evaluate JavaScript', selector, script)

    def _count(self, selector):
        """Count current matches; prefer scoped unique selectors over an arbitrary first match."""
        return int(self._kw('Get Element Count', selector))

    def _visible(self, selector):
        """Check visibility of an existing match without silently accepting hidden messages."""
        return self._count(selector + ':visible') > 0

    def _text(self, selector):
        """Read user-visible text for an exact assertion or price oracle."""
        return self._kw('Get Text', selector)

    def _money(self, selector):
        """Parse one en-locale UI price as Decimal; fail on ambiguous/missing amounts."""
        amounts = re.findall(r'-?\d[\d,]*\.\d{2}', self._text(selector))
        if len(amounts) != 1:
            raise AssertionError('Expected exactly one displayed amount at ' + selector)
        return Decimal(amounts[0].replace(',', ''))

    def _assert_money(self, selector, expected):
        """Compare independent fixture arithmetic with the displayed monetary amount."""
        actual = self._money(selector)
        if actual != Decimal(expected):
            raise AssertionError('Displayed amount differs: ' + str(actual) + ' != ' + str(expected))

    def _home(self):
        """Reach the home page via its actual navigation link after the initial entry."""
        self._kw('Click', 'css=.fc-menu a[href="/"]')

    def _open_registration(self):
        """Open the registration link exposed by the anonymous native login menu."""
        self._kw('Click', 'css=#login-dropdown > a')
        self._kw('Click', 'css=#login-dropdown a[href^="/register/"]')
        self._kw('Wait For Elements State', 'css=input[name="password2"]', 'visible')

    def _secret(self, selector, key):
        """Resolve an environment secret in Browser, avoiding password keyword arguments."""
        if os.environ[key] == '':
            self._kw('Fill Text', selector, '')
        else:
            self.browser.fill_secret(selector, '%' + key)

    def _fill_registration(self, inputs):
        """Enter the exact literal values already materialized in the reviewed plan."""
        for field in ('username', 'email'):
            self._kw('Fill Text', 'css=input[name="' + field + '"]', inputs[field])
        for field in ('password1', 'password2'):
            key = 'ROBOT_CASE_' + field.upper()
            os.environ[key] = inputs[field]
            self._secret('css=input[name="' + field + '"]', key)

    def _registration_rejection(self, case):
        """Assert rejection of the changed registration field, not merely absence of a redirect."""
        self._open_registration()
        self._fill_registration(case['inputs'])
        field = 'css=input[name="' + case['field'] + '"]'
        self._kw('Click', 'css=form:has(input[name="password2"]) button[type="submit"]')
        def rejected():
            """Accept a native constraint or the rendered server error on the changed field."""
            if not self._count(field):
                return False
            return self._read(field, '(el) => !el.checkValidity() || !!el.closest(".has-error")')
        self._until(rejected, 'registration error on ' + case['field'])
        if '/register/' not in self._kw('Get Url') or self._count('css=.top-nav a[href*="/logout/"]'):
            raise AssertionError('Invalid registration unexpectedly authenticated or left the form.')

    def _login(self, username, password):
        """Submit the native quick-login form using a visible menu and secret reference."""
        self._kw('Click', 'css=#login-dropdown > a')
        form = 'css=#login-dropdown form[action="/login/"]'
        self._kw('Fill Text', form + ' input[name="username"]', username)
        os.environ['ROBOT_CASE_LOGIN_PASSWORD'] = password
        self._secret(form + ' input[name="password"]', 'ROBOT_CASE_LOGIN_PASSWORD')
        self._kw('Click', form + ' button[type="submit"]')

    def _login_rejection(self, case):
        """Change exactly one credential and require a native input or server login error."""
        self._login(case['inputs']['username'], case['inputs']['password'])
        self._until(lambda: self._visible('css=.alert-danger') or self._visible('css=.has-error') or
                    bool(self._read('css=form:has(input[name="password"]) input[name="' + case['field'] + '"]', '(el) => !el.checkValidity()')),
                    'visible login rejection')
        if self._count('css=.top-nav a[href*="/logout/"]'):
            raise AssertionError('Invalid login unexpectedly authenticated.')

    def _search(self, query):
        """Submit the visible search modal; use native links rather than direct result URLs."""
        self._kw('Click', 'css=#search-modal-toggler')
        self._kw('Fill Text', 'css=#site-search', query)
        self._kw('Click', 'css=#search-modal form button[type="submit"]')
        self._kw('Wait For Elements State', 'css=#product_search', 'visible')
        self._kw('Get Property', 'css=#product_search input[name="q"]', 'value', '==', query)

    def _open_product(self, sku, inspect_gallery=False):
        """Open an exact product; quantity probes do not depend on optional zoom checks."""
        product = self.catalogue[sku]
        if inspect_gallery:
            self._at(['TC-TK-001'])
        self._search(product['name'])
        card = 'css=.product-card:has(.name:text-is(' + json.dumps(product['name']) + '))'
        if self._count(card) != 1:
            raise AssertionError('Expected one search card for fixture product ' + sku)
        if inspect_gallery:
            self._capture(['TC-TK-001'], 'search-' + sku)
            self._at(['TC-SP-001'])
        self._kw('Click', card + ' > a[rel="product-detail"]')
        heading = 'css=.product-main h1.product-name:visible'
        self._kw('Wait For Elements State', heading, 'visible')
        if self._count(heading) != 1:
            raise AssertionError('Expected one visible responsive product heading.')
        self._kw('Get Text', heading, '==', product['name'])
        self._kw('Get Text', 'css=body', 'contains', product['description'])
        self._kw('Get Text', 'css=body', 'contains', product['size'])
        self._assert_money('css=#product-price-section .product-price strong:visible', product['price'])
        self._kw('Wait For Elements State', 'css=form.add-to-basket input[name="quantity"]', 'visible')
        if inspect_gallery:
            self._inspect_product_gallery()
            self._capture(['TC-SP-001'], 'details-' + sku)

    def _inspect_product_gallery(self):
        """Check the actual visible photograph, without requiring wrapper dimensions.

        Lightbox wrappers can contain positioned children. Visibility belongs to
        the image being tested, rather than an ancestor's own bounding box.
        A failed image check still fails the product-detail journey.
        """
        image = 'css=.sl-wrapper .sl-image img:visible'
        self._kw('Click', 'css=.product-image .item.active a.thumbnail')
        self._kw('Wait For Elements State', image, 'visible')
        if self._count(image) != 1:
            raise AssertionError('Expected one visible enlarged product photograph.')
        self._until(lambda: self._read(image, '(el) => el.complete && el.naturalWidth > 0'),
                    'loaded product photograph')
        self._capture(['TC-SP-001'], 'product-image')
        self._kw('Press Keys', 'css=body', 'Escape')
        self._kw('Wait For Elements State', image, 'hidden')

    def _cart_count(self):
        """Read the native navigation count, including zero in a fresh browser session."""
        match = re.search(r'\((\d+)\)', self._text('css=#navigation-basket-partial'))
        if not match:
            raise AssertionError('Navigation basket count is missing.')
        return int(match[1])

    def _open_cart(self):
        """Follow the cart dropdown link that the customer can actually click."""
        self._kw('Click', 'css=#navigation-basket-partial > li.cart > a.dropdown-toggle')
        self._kw('Click', 'css=#navigation-basket-partial a[href="/basket/"]')

    def _quantity(self, case):
        """Exercise BVA/EP without creating an order or consuming boundary stock."""
        self._login(case['inputs']['account']['username'], case['inputs']['account']['password'])
        self._kw('Wait For Elements State', 'css=.top-nav a[href*="/logout/"]', 'attached')
        self._open_product(self.model['quantity_product'])
        if self._cart_count() != 0:
            raise AssertionError('Quantity probes require an empty isolated session basket.')
        field = 'css=form.add-to-basket input[name="quantity"]'
        spec = self.model['quantity_model']['fields']['quantity']
        if any(Decimal(self._kw('Get Attribute', field, key)) != Decimal(spec[key]) for key in ('min', 'step')):
            raise AssertionError('Quantity control differs from the declared min/step specification.')
        self._kw('Fill Text', field, case['value'])
        # Leaving the field triggers upstream price/availability refresh before Add.
        refresh = None
        if self._read(field, '(el) => el.checkValidity()') and case['value'] != '1':
            refresh = self._kw('Promise To', 'Wait For Response', 'matcher=**/xtheme/product_price*', 'timeout=15s')
        self._kw('Press Keys', field, 'Tab')
        if refresh is not None:
            self._kw('Wait For', refresh)
        button = 'css=.btn-add-to-cart button[type="submit"]'
        if case['expected'] == 'accepted':
            self._assert_money('css=#product-price-section .product-price strong:visible', Decimal(self.catalogue[self.model['quantity_product']]['price']) * Decimal(case['value']))
            self._kw('Click', button)
            self._until(lambda: self._cart_count() == int(case['value']), 'accepted basket quantity')
            self._open_cart()
            self._kw('Get Property', 'css=#update_basket_form .line_quantity', 'value', '==', case['value'])
            self._assert_money('css=.basket-summary .total-price', Decimal(self.catalogue[self.model['quantity_product']]['price']) * Decimal(case['value']))
        else:
            if not self._read(field, '(el) => el.checkValidity()'):
                self._kw('Click', button)
            else:
                # Observe the native error without requiring its transient ancestor class.
                if not self._kw('Get Property', button, 'disabled'):
                    self._kw('Click', button)
                def rejected():
                    """Fail immediately if the application accepted an above-stock quantity."""
                    count = self._cart_count()
                    if count:
                        raise AssertionError('Expected quantity rejection, but the basket now contains ' + str(count) + ' items. Check stock configuration and application behavior.')
                    return bool(self._kw('Get Property', button, 'disabled')) or self._quantity_error()
                try:
                    self._until(rejected, 'visible quantity or stock rejection')
                except AssertionError as error:
                    if 'Timed out' not in str(error):
                        raise
                    raise AssertionError('No visible quantity/stock rejection was observed for quantity ' + case['value'] +
                                         '; basket count=' + str(self._cart_count()) +
                                         '; add button disabled=' + str(self._kw('Get Property', button, 'disabled')) +
                                         '. Inspect the product page and basket response; this is not a passing rejection.') from error
            if self._cart_count() != 0:
                raise AssertionError('Rejected quantity changed the customer basket.')

    def _quantity_error(self):
        """Require a visible domain error, excluding a generic network/server failure."""
        messages = self._read('css=body', """(body) =>
            Array.from(body.querySelectorAll('.cover-wrap #error-msg, .alert-danger, .alert-warning, .errorlist, .not-orderable'))
                .filter(el => { const box = el.getBoundingClientRect();
                    if (box.width <= 0 || box.height <= 0) return false;
                    for (let node = el; node && node.nodeType === 1; node = node.parentElement) {
                        const style = getComputedStyle(node);
                        if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) return false;
                    }
                    return true; })
                .map(el => el.innerText)""")
        return any(re.search(r'quantity|stock|available|integer|minimum|multiples|whole', text, re.I) for text in messages)

    def _activation_link(self, recipient, started):
        """Read only newly delivered mail for this recipient, never query auth tables."""
        def delivered():
            """Locate the genuine activation link in a matching MIME email body."""
            for path in sorted(Path('/app/.runtime/data/mail').glob('*'), reverse=True):
                if not path.is_file() or path.stat().st_mtime < started:
                    continue
                message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
                if recipient.lower() not in {address.lower() for _, address in getaddresses(message.get_all('To', []))}:
                    continue
                for part in message.walk():
                    if part.get_content_type() not in ('text/plain', 'text/html'):
                        continue
                    body = str(part.get_content())
                    matches = re.findall(r'https?://[^\s<>"\x27]+/activate/[A-Za-z0-9_]+/', unescape(body))
                    for link in matches:
                        if urlsplit(link).netloc != urlsplit(self.base).netloc:
                            raise AssertionError('Activation email origin differs from this store.')
                        self.activation = link
                        return True
            return False
        self._until(delivered, 'activation mail for the new customer; check native registration notification configuration')
        return self.activation

    def _logout(self):
        """Use the native account dropdown and logout link, preserving the user journey."""
        self._kw('Click', 'css=.top-nav li.dropdown:has(a[href*="/logout/"]) > a.dropdown-toggle')
        self._kw('Click', 'css=.top-nav a[href*="/logout/"]')
        self._kw('Wait For Elements State', 'css=#login-dropdown', 'visible')

    def _toggle_checkbox(self, selector, checked):
        """Use the visible associated label, including when native CSS hides the input."""
        if self._kw('Get Property', selector, 'checked') != checked:
            control_id = self._kw('Get Attribute', selector, 'id')
            self._kw('Click', 'css=label[for=' + json.dumps(control_id) + ']')
        if self._kw('Get Property', selector, 'checked') != checked:
            raise AssertionError('Checkbox did not reach the requested user-visible state.')

    def _select_method(self, field, name):
        """Click the visible method label and verify its actual radio is selected."""
        row = 'css=.checkout-method-radio:has(.name:text-is(' + json.dumps(name) + '))'
        self._kw('Click', row + ' > label')
        if not self._kw('Get Property', row + ' input[name="' + field + '"]', 'checked'):
            raise AssertionError('Native shipping/payment radio was not selected.')

    def _addresses(self, identity, inputs):
        """Check required billing street, copy mode and independent shipping before continuing."""
        self._at(['TC-DC-001'])
        addresses = {self.model['billing_address']: inputs['billing'], self.model['shipping_address']: inputs['shipping']}
        for kind, address_id in [('billing', self.model['billing_address']), ('shipping', self.model['shipping_address'])]:
            address = addresses[address_id]
            for field, value in {'name': inputs['recipient'], 'email': identity['email'], 'phone': inputs['phone'],
                                 'street': address['street'], 'street2': address.get('street2', ''),
                                 'postal_code': address['postal_code'], 'city': address['city']}.items():
                self._kw('Fill Text', 'css=input[name="' + kind + '-' + field + '"]', value)
            self._kw('Select Options By', 'css=select[name="' + kind + '-country"]', 'value', address['country'])
        self._toggle_checkbox('css=#same_as_billing', True)
        billing_street = addresses[self.model['billing_address']]['street']
        for field in ('name', 'email', 'phone', 'street', 'street2', 'postal_code', 'city', 'country'):
            tag = 'select' if field == 'country' else 'input'
            expected = self._kw('Get Property', 'css=' + tag + '[name="billing-' + field + '"]', 'value')
            self._kw('Get Property', 'css=' + tag + '[name="shipping-' + field + '"]', 'value', '==', expected)
        self._capture(['TC-DC-001'], 'billing-copy')
        self._at(['TC-DC-002'])
        self._toggle_checkbox('css=#same_as_billing', False)
        for field in ('street', 'street2', 'postal_code', 'city'):
            address = addresses[self.model['shipping_address']]
            self._kw('Fill Text', 'css=input[name="shipping-' + field + '"]', address.get(field, ''))
        self._capture(['TC-DC-002'], 'separate-shipping')
        self._at(['TC-DC-003'])
        # Single missing address field; all other fields and both countries remain valid.
        self._kw('Fill Text', 'css=input[name="billing-street"]', '')
        self._kw('Click', 'css=form button[type="submit"]:has-text("Continue")')
        field = 'css=input[name="billing-street"]'
        self._until(lambda: self._read(field, '(el) => !el.checkValidity() || !!el.closest(".has-error")'), 'required billing street rejection')
        self._capture(['TC-DC-003'], 'billing-street-validation')
        self._kw('Fill Text', field, billing_street)
        self._kw('Click', 'css=form button[type="submit"]:has-text("Continue")')
        self._kw('Wait For Elements State', 'css=form#methods', 'visible')

    def _coupon(self, subtotal, inputs):
        """Cover absent, unknown, valid and removed code outcomes without duplicating orders."""
        code = inputs['coupon']['code']
        if not code:
            raise AssertionError('Customer suite needs the active configured COUPON_CODE; run setup after configuring it.')
        self._at(['TC-KM-001'])
        self._assert_money('css=.basket-summary .total-price', subtotal)
        self._capture(['TC-KM-001'], 'coupon-empty')
        self._at(['TC-KM-002'])
        self._kw('Fill Text', 'css=#discount-code', inputs['unknown_coupon'])
        pending = self._kw('Promise To', 'Wait For Alert', 'action=accept', 'timeout=15s')
        self._kw('Click', 'css=#submit-code')
        dialog = self._kw('Wait For', pending)
        if 'Coupon is not available' not in dialog:
            raise AssertionError('Expected the native unavailable-coupon message.')
        self._assert_money('css=.basket-summary .total-price', subtotal)
        if self._count('css=.basket-used-code'):
            raise AssertionError('Unknown coupon was applied.')
        self._capture(['TC-KM-002'], 'unknown-coupon-after-dialog')
        self._at(['TC-KM-003'])
        discounted = (subtotal * (1 - Decimal(self.store['welcome_offer']['percentage']))).quantize(Decimal('0.01'))
        self._kw('Fill Text', 'css=#discount-code', code)
        self._kw('Click', 'css=#submit-code')
        self._kw('Wait For Elements State', 'css=.basket-used-code .basket-code', 'visible')
        self._kw('Get Text', 'css=.basket-code', '==', code)
        self._assert_money('css=.basket-summary .total-price', discounted)
        self._capture(['TC-KM-003'], 'coupon-applied')
        self._at(['TC-KM-004'])
        self._kw('Click', 'css=.basket-remove-code-btn')
        self._kw('Wait For Elements State', 'css=.basket-used-code', 'detached')
        self._assert_money('css=.basket-summary .total-price', subtotal)
        self._capture(['TC-KM-004'], 'coupon-removed')
        self._kw('Fill Text', 'css=#discount-code', code)
        self._kw('Click', 'css=#submit-code')
        self._kw('Wait For Elements State', 'css=.basket-code', 'visible')
        self._assert_money('css=.basket-summary .total-price', discounted)
        return discounted

    def _checkout_methods(self, discounted):
        """Quote all three available carriers with COD, then retain Careful delivery for the order."""
        ordered = [row for row in self.carriers if row['id'] != self.model['final_carrier']] + [
            row for row in self.carriers if row['id'] == self.model['final_carrier']]
        for index, carrier in enumerate(ordered):
            business_id = 'TC-VC-' + str(next(i for i, row in enumerate(self.carriers, 1) if row['id'] == carrier['id'])).zfill(3)
            self._at([business_id])
            if index:
                self._kw('Click', 'css=.nav-pills a[href*="/checkout/methods/"]')
            name = carrier['name'] + ' - ' + carrier['service']
            self._select_method('shipping_method', name)
            self._select_method('payment_method', 'Pay on delivery')
            self._kw('Click', 'css=form#methods button[type="submit"]')
            self._kw('Wait For Elements State', 'css=#confirm_form', 'visible')
            total = discounted + Decimal(carrier['fee'])
            self._assert_money('css=.basket-table tfoot .total-price:not(.text-muted)', total)
            self._kw('Get Text', 'css=body', 'contains', name)
            self._kw('Get Text', 'css=body', 'contains', 'Pay on delivery')
            self._capture([business_id], 'carrier-confirmation')
        return total

    def _assert_order_lines(self):
        """Check persisted/displayed unit prices and quantities for each exact order product."""
        for sku in self.model['order_products']:
            product = self.catalogue[sku]
            row = 'css=.basket-table tbody tr:has(td:nth-child(2):has-text(' + json.dumps(product['name']) + '))'
            if self._count(row) != 1:
                raise AssertionError('Expected exactly one order row for ' + sku)
            self._assert_money(row + ' td:nth-child(3)', product['price'])
            self._assert_money(row + ' .line-total', product['price'])
            quantity = ' '.join(self._text(row + ' td:nth-child(4)').split())
            if not re.fullmatch(r'1(?:\s+pcs)?', quantity):
                raise AssertionError('Order quantity is not one for ' + sku)
        self._kw('Get Text', 'css=.basket-table', 'contains', self.store['welcome_offer']['name'])

    def _journey(self, case):
        """Register and follow the same customer through three searches to exact order history."""
        self._at(['TC-DK-001'])
        self._open_registration()
        inputs = case['inputs']
        identity = inputs['registration']
        started = time.time() - 1
        self._fill_registration(identity)
        self._kw('Click', 'css=form:has(input[name="password2"]) button[type="submit"]')
        # The mailbox is an external customer channel; use the actual delivered link.
        self._kw('New Page', self._activation_link(identity['email'], started))
        self._kw('Wait For Elements State', 'css=.top-nav a[href*="/logout/"]', 'attached')
        self._logout()
        self._at(['TC-DK-001', 'TC-DN-001'])
        self._login(identity['username'], identity['password1'])
        self._kw('Wait For Elements State', 'css=.top-nav a[href*="/logout/"]', 'attached')
        self._capture(['TC-DK-001', 'TC-DN-001'], 'activated-login')
        self._at(['TC-TK-002'])
        self._search(inputs['absent_search'])
        if self._count('css=.product-card'):
            raise AssertionError('A unique absent search term returned a product card.')
        self._capture(['TC-TK-002'], 'empty-search')
        self._home()
        subtotal = Decimal('0')
        for index, sku in enumerate(self.model['order_products'], start=1):
            self._open_product(sku, inspect_gallery=True)
            self._at(['TC-GH-010'])
            self._kw('Fill Text', 'css=form.add-to-basket input[name="quantity"]', '1')
            self._kw('Click', 'css=.btn-add-to-cart button[type="submit"]')
            self._until(lambda: self._cart_count() == index, 'three-product basket progress')
            subtotal += Decimal(self.catalogue[sku]['price'])
        self._open_cart()
        if self._count('css=#update_basket_form .single-item') != 3:
            raise AssertionError('Basket must contain three distinct product lines.')
        for sku in self.model['order_products']:
            name = self.catalogue[sku]['name']
            row = 'css=#update_basket_form .single-item:has(.name a:text-is(' + json.dumps(name) + '))'
            self._kw('Get Property', row + ' .line_quantity', 'value', '==', '1')
        self._capture(['TC-GH-010'], 'three-product-basket')
        discounted = self._coupon(subtotal, inputs)
        self._kw('Click', 'css=a.btn-checkout')
        self._kw('Wait For Elements State', 'css=input[name="billing-street"]', 'visible')
        self._addresses(identity, inputs)
        total = self._checkout_methods(discounted)
        self._at(['TC-DH-001'])
        self._toggle_checkbox('css=#confirm_form input[name="accept_terms"]', False)
        self._kw('Click', 'css=#confirm_form button[type="submit"]')
        self._until(lambda: self._read('css=input[name="accept_terms"]', '(el) => !el.checkValidity() || !!el.closest(".has-error")'), 'terms rejection')
        if '/checkout/confirm/' not in self._kw('Get Url'):
            raise AssertionError('Order completed without accepting terms.')
        self._capture(['TC-DH-001'], 'terms-validation')
        self._at(['TC-DH-002'])
        self._toggle_checkbox('css=#confirm_form input[name="accept_terms"]', True)
        self._kw('Fill Text', 'css=#confirm_form textarea[name="comment"]', inputs['order_comment'])
        self._kw('Click', 'css=#confirm_form button[type="submit"]')
        self._kw('Get Text', 'css=body', 'contains', 'Your order has been received.')
        completed = re.search(r'/order/complete/([^/]+)/', urlsplit(self._kw('Get Url')).path)
        if not completed:
            raise AssertionError('Expected native order completion URL.')
        order_pk = completed[1]
        self._assert_money('css=.basket-table tfoot .total-price:not(.text-muted)', total)
        self._assert_order_lines()
        self._kw('Get Text', 'css=body', 'contains', 'Pay on delivery')
        carrier = next(row for row in self.carriers if row['id'] == self.model['final_carrier'])
        self._kw('Get Text', 'css=body', 'contains', carrier['name'] + ' - ' + carrier['service'])
        if self._cart_count() != 0:
            raise AssertionError('Basket was not emptied after placing the order.')
        self._capture(['TC-DH-002'], 'order-received')
        self._at(['TC-LS-001'])
        self._kw('Click', 'css=.top-nav li.dropdown:has(a[href="/order-history/"]) > a.dropdown-toggle')
        self._kw('Click', 'css=.top-nav a[href="/order-history/"]')
        rows = 'css=table tbody tr:has(a[href^="/order-history/"])'
        if self._count(rows) != 1:
            raise AssertionError('The newly registered customer must see exactly one order.')
        if self._kw('Get Attribute', rows + ' a', 'href') != '/order-history/' + order_pk + '/':
            raise AssertionError('History link is not the order just created.')
        identifier = self._text(rows + ' td:first-child').strip()
        self._kw('Click', rows + ' a')
        self._kw('Get Text', 'css=h2:text-is(' + json.dumps('Order ' + identifier) + ')', '==', 'Order ' + identifier)
        self._assert_money('css=tr:has(th:text-is("Total Price")) td', total)
        self._kw('Get Text', 'css=tr:has(th:text-is("Payment Status")) td', '==', 'not paid')
        self._assert_order_lines()
        self._kw('Get Text', 'css=body', 'contains', identity['email'])
        for address_id in (self.model['billing_address'], self.model['shipping_address']):
            address = next(row for row in self.store['addresses'] if row['id'] == address_id)
            self._kw('Get Text', 'css=body', 'contains', address['street'])
        self._capture(['TC-LS-001', 'TC-HT-001'], 'order-history')
        self.robot.log('Verified customer order ' + identifier + '; COD selected, no captured payment.', 'INFO')

    def _at(self, case_ids):
        """Identify the current business checkpoint before performing its actions."""
        self.active_business_cases = list(case_ids)

    def _capture(self, case_ids, checkpoint, role='checkpoint'):
        """Save actual page images; a capture problem must not replace a test failure."""
        for case_id in dict.fromkeys(case_ids):
            try:
                target = self.evidence.target(case_id, checkpoint)
                actual = self._kw('Take Screenshot', str(target), 'fullPage=True', 'log_screenshot=True')
                self.evidence.record(actual or target, case_id, self.active_robot_id, checkpoint, role)
            except Exception as error:
                try:
                    self.evidence.capture_error(case_id, self.active_robot_id, checkpoint, error)
                except OSError:
                    pass
                self.robot.log('Screenshot capture unavailable for ' + case_id + '; see the evidence manifest.', 'WARN')

    @keyword('Execute Customer Case')
    def execute_customer_case(self, payload):
        """Decode one planned case and run its UI stage in a fresh browser/context."""
        case = json.loads(base64.b64decode(payload, validate=True).decode())
        if semantic_hash(case) != self.model['_provenance']['case_sha256'].get(case.get('id')):
            raise ValueError('Customer payload differs from its frozen case; regenerate the suite.')
        extra_outcomes = {'basket_update': {'accepted', 'rejected', 'unchanged'},
                          'address_book': {'accepted', 'rejected', 'bounded'},
                          'password_change': {'accepted', 'rejected', 'login_required'}}
        if case['expected'] not in extra_outcomes.get(case['stage'], {'accepted', 'rejected'} if case['stage'] == 'quantity' else {'order_received_not_paid'} if case['stage'] == 'e2e' else {'rejected'}):
            raise ValueError('Unsupported expected outcome for customer stage.')
        self.robot = BuiltIn()
        self.browser = self.robot.get_library_instance('Browser')
        if self.evidence is None:
            self.evidence = EvidenceRun(Path(__file__).resolve().parents[2], self.model['_provenance']['model_sha256'])
            self.robot.run_keyword('Set Suite Metadata', 'Evidence Run ID', self.evidence.run_id)
            self.robot.run_keyword('Set Suite Metadata', 'Evidence Manifest', self.evidence.manifest_path.relative_to(self.evidence.app).as_posix())
        self.active_robot_id = case['id']
        definitions = json.loads((Path(__file__).resolve().parents[2] / 'tests/data/CUSTOMER_CASE_TEXT.json').read_text(encoding='utf-8'))
        definitions['cases'].extend(json.loads((Path(__file__).resolve().parents[2] / 'tests/data/CUSTOMER_EXTENSION_TEXT.json').read_text())['cases'])
        business_ids = [row['id'] for row in definitions['cases'] if row['robot_ids'] == [case['id']]]
        self._at(business_ids if case['stage'] != 'e2e' else ['TC-HT-001'])
        try:
            self._kw('New Browser', 'chromium', 'headless=True')
            self._kw('New Context', 'viewport={"width": 1440, "height": 1000}')
            self._kw('New Page', self.base + '/')
            stage = case['stage']
            if stage == 'basket_update':
                self._basket_update(case)
            elif stage == 'address_book':
                self._address_book(case)
            elif stage == 'password_change':
                self._password_change(case)
            elif stage == 'quantity':
                self._quantity(case)
            elif stage == 'registration':
                self._registration_rejection(case)
            elif stage == 'login':
                self._login_rejection(case)
            elif stage == 'e2e':
                self._journey(case)
            else:
                raise ValueError('Unknown customer UI stage.')
            if stage != 'e2e':
                self._capture(business_ids, 'result')
            self.evidence.finish_test(case['id'], 'PASS')
        except Exception:
            current = self.active_business_cases + (['TC-HT-001'] if case['stage'] == 'e2e' else [])
            self._capture(current, 'failure', role='failure')
            try:
                self.evidence.finish_test(case['id'], 'FAIL')
            except OSError:
                self.robot.log('Evidence status could not be saved; the original test failure is preserved.', 'WARN')
            raise

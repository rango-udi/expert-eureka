"""Customer UI extensions using native links, forms and observable persistence."""
from decimal import Decimal
import json
import os


class CustomerExtensionKeywords:
    """Reuse the customer Browser adapter without application imports or API mutations."""

    def _extra_login(self, account):
        """Authenticate with a reviewed dedicated account and verify the visible session."""
        self._login(account['username'], account['password'])
        self._kw('Wait For Elements State', 'css=.top-nav a[href*="/logout/"]', 'attached')

    def _extra_account(self):
        """Open account details using the native authenticated dropdown."""
        self._kw('Click', 'css=.top-nav li.dropdown:has(a[href*="/logout/"]) > a.dropdown-toggle')
        self._kw('Click', 'css=.top-nav a[href="/customer/"]')

    def _extra_book(self):
        """Follow the address-book sidebar exposed on account pages."""
        self._kw('Click', 'css=.section-navigation a[href="/address-book/"]')
        self._kw('Wait For Elements State', 'css=.user-account-address', 'visible')

    def _extra_add(self, sku, quantity, count):
        """Add through the product form and wait for the exact new navigation count."""
        self._open_product(sku)
        field = 'css=form.add-to-basket input[name="quantity"]'
        self._kw('Fill Text', field, quantity)
        if quantity != '1':
            pending = self._kw('Promise To', 'Wait For Response', 'matcher=**/xtheme/product_price*', 'timeout=15s')
            self._kw('Press Keys', field, 'Tab')
            self._kw('Wait For', pending)
        self._kw('Click', 'css=.btn-add-to-cart button[type="submit"]')
        self._until(lambda: self._cart_count() == count, 'exact basket count after adding')

    def _extra_basket_line(self, sku):
        """Resolve one native basket card by its textual product heading, not its image link."""
        self._kw('Wait For Elements State', 'css=#update_basket_form', 'visible')
        selector = 'css=#update_basket_form .single-item:has(.product-details .name a.product-name:text-is(' + json.dumps(self.catalogue[sku]['name']) + '))'
        count = self._count(selector)
        if count != 1:
            raise AssertionError('Expected exactly one native basket card for ' + sku + '; found ' + str(count) + '. Inspect the basket DOM and screenshot; no quantity/delete action was attempted.')
        return selector

    def _basket_update(self, case):
        """Inspect update, removal and repeated-add behavior independently of checkout."""
        inputs = case['inputs']
        self._extra_login(inputs['account'])
        if self._cart_count() != 0:
            raise AssertionError('Basket extensions require a fresh empty session.')
        sku = inputs['product_sku']
        operation = case['operation']
        self._extra_add(sku, inputs['initial_quantity'], int(inputs['initial_quantity']))
        if operation == 'repeat_add':
            self._extra_add(sku, inputs['second_quantity'], 3)
        elif operation == 'delete_one':
            self._extra_add(inputs['second_sku'], inputs['second_quantity'], 3)
        self._open_cart()
        row = self._extra_basket_line(sku)
        field = row + ' input.line_quantity'
        if operation == 'update':
            value = inputs['value']
            if Decimal(self._kw('Get Attribute', field, 'min')) != 1 or Decimal(self._kw('Get Attribute', field, 'step')) != 1:
                raise AssertionError('Basket min/step differs from the reviewed whole-bottle domain.')
            if value != '2':
                pending = self._kw('Promise To', 'Wait For Response', 'matcher=**/basket/', 'timeout=15s')
                self._kw('Fill Text', field, value)
                self._kw('Press Keys', field, 'Tab')
                self._kw('Wait For', pending)
                self._kw('Wait For Load State', 'networkidle')
            if case['expected'] == 'rejected':
                self._extra_update_rejection(case, field)
                self._capture([case['business_id']], 'update-validation')
            expected = int(value) if case['expected'] == 'accepted' else 2
            self._kw('Reload')
            self._kw('Get Property', field, 'value', '==', str(expected))
            if self._cart_count() != expected:
                raise AssertionError('Saved basket count differs after update/rejection.')
            self._assert_money('css=.basket-summary .total-price', Decimal(self.catalogue[sku]['price']) * expected)
        elif operation in ('delete_one', 'delete_last'):
            self._kw('Click', row + ' button[name^="delete_"]')
            expected = 1 if operation == 'delete_one' else 0
            self._until(lambda: self._cart_count() == expected, 'basket count after deleting a product')
            self._kw('Reload')
            if self._count(row):
                raise AssertionError('The deleted product still has a basket row.')
            if operation == 'delete_one':
                self._assert_money('css=.basket-summary .total-price', self.catalogue[inputs['second_sku']]['price'])
            elif self._count('css=#update_basket_form input.line_quantity'):
                raise AssertionError('Deleting the final line left product controls behind.')
        else:
            if self._count('css=#update_basket_form input.line_quantity') != 1 or self._cart_count() != 3:
                raise AssertionError('Repeated additions did not merge into one three-bottle line.')
            self._kw('Get Property', field, 'value', '==', '3')
            self._assert_money('css=.basket-summary .total-price', Decimal(self.catalogue[sku]['price']) * 3)

    def _extra_update_rejection(self, case, field):
        """Require a domain message and expose saved state when rejection remains unobserved."""
        try:
            self._until(self._quantity_error, 'native basket quantity or stock error')
        except AssertionError as error:
            self._capture([case['business_id']], 'unobserved-update-rejection', role='failure')
            self._kw('Reload')
            actual = self._kw('Get Property', field, 'value') if self._count(field) else 'missing product line'
            raise AssertionError('No visible native basket rejection for attempted quantity ' + case['inputs']['value'] +
                                 '; saved quantity after reload=' + str(actual) + '; expected unchanged quantity=2. '
                                 'Inspect native warning rendering and purchase-multiple/stock configuration.') from error

    def _extra_address_form(self, inputs):
        """Fill the native address and saved-address form prefixes with literal data."""
        title = 'css=input[name="saved_address-title"]'
        if int(self._kw('Get Attribute', title, 'maxlength')) != 255:
            raise AssertionError('Saved-address title maxlength differs from the reviewed 255-character limit.')
        self._kw('Fill Text', title, '')
        self._kw('Type Text', title, inputs['title'])
        for key in ('role', 'status'):
            self._kw('Select Options By', 'css=select[name="saved_address-' + key + '"]', 'value', inputs[key])
        for key, value in inputs['address'].items():
            selector = 'css=' + ('select' if key == 'country' else 'input') + '[name="address-' + key + '"]'
            if key == 'country':
                self._kw('Select Options By', selector, 'value', value)
            else:
                self._kw('Fill Text', selector, value)
        self._kw('Click', 'css=form:has(input[name="saved_address-title"]) button[type="submit"]')

    def _extra_address_values(self, inputs, title):
        """Compare saved fields after navigation rather than trusting a success toast."""
        self._kw('Get Property', 'css=input[name="saved_address-title"]', 'value', '==', title)
        for key in ('role', 'status'):
            self._kw('Get Property', 'css=select[name="saved_address-' + key + '"]', 'value', '==', inputs[key])
        for key, value in inputs['address'].items():
            self._kw('Get Property', 'css=' + ('select' if key == 'country' else 'input') + '[name="address-' + key + '"]', 'value', '==', value)

    def _extra_address_card(self, title):
        """Select exactly the additional-address card by its saved heading."""
        return 'css=.user-account-address .content-block:has(:text-is(' + json.dumps(title) + '))'

    def _extra_address_links(self):
        """Discover the created address by the server-issued edit path, never guess an ID."""
        url = self._kw('Get Url')
        path = url.split('/address-book/edit/', 1)[1]
        if not path.isdigit():
            raise AssertionError('Saving the address did not reach its native edit URL.')
        return '/address-book/edit/' + path, '/address-book/delete/' + path

    def _extra_delete_address(self, edit, delete):
        """Delete only the exact address created by this case through its own UI link."""
        self._extra_book()
        self._kw('Click', 'css=.user-account-address a[href=' + json.dumps(delete) + ']')
        self._kw('Wait For Elements State', 'css=.user-account-address', 'visible')
        if self._count('css=.user-account-address a[href=' + json.dumps(edit) + ']'):
            raise AssertionError('The created address still appears after deletion.')

    def _address_book(self, case):
        """Exercise persistence and ownership without changing default checkout addresses."""
        inputs = case['inputs']
        self._extra_login(inputs['account'])
        self._extra_account()
        self._extra_book()
        title = inputs['title'][:255]
        if title and self._count('css=.user-account-address :text-is(' + json.dumps(title) + ')'):
            raise AssertionError('A prior extension address has this exact title. Review its evidence and remove it through the owning account before rerunning.')
        self._kw('Click', 'css=.user-account-address a[href="/address-book/edit/new"]')
        self._extra_address_form(inputs)
        if case['expected'] == 'rejected':
            field = 'saved_address-title' if not inputs['title'] else 'address-street'
            selector = 'css=input[name="' + field + '"]'
            self._until(lambda: not self._read(selector, '(el) => el.checkValidity()') or self._visible('css=.has-error, .errorlist'), 'address-field rejection')
            self._capture([case['business_id']], 'address-validation')
            self._extra_book()
            if title and self._count('css=.user-account-address :text-is(' + json.dumps(title) + ')'):
                raise AssertionError('Invalid address was saved.')
            return
        self._kw('Wait For Elements State', 'css=.alert-success', 'visible')
        edit, delete = self._extra_address_links()
        self._extra_book()
        self._kw('Click', 'css=.user-account-address a[href=' + json.dumps(edit) + ']')
        self._extra_address_values(inputs, title)
        if case['operation'] == 'edit':
            self._kw('Fill Text', 'css=input[name="address-street"]', inputs['updated_street'])
            self._kw('Click', 'css=form:has(input[name="saved_address-title"]) button[type="submit"]')
            self._extra_book()
            self._kw('Click', 'css=.user-account-address a[href=' + json.dumps(edit) + ']')
            self._kw('Get Property', 'css=input[name="address-street"]', 'value', '==', inputs['updated_street'])
        self._capture([case['business_id']], 'saved-address')
        if case['operation'] == 'ownership':
            self._logout()
            self._extra_login(inputs['other_account'])
            self._extra_account()
            self._extra_book()
            if self._count('css=.user-account-address a[href=' + json.dumps(edit) + ']'):
                raise AssertionError('Another account can list the owner address.')
            # Recorded foreign resource links intentionally test authorization boundaries.
            self._kw('Go To', self.base + edit)
            field = 'css=input[name="saved_address-title"]'
            if self._count(field) and self._kw('Get Property', field, 'value') != '':
                raise AssertionError('Another account can read the owner address edit data.')
            street = 'css=input[name="address-street"]'
            if self._count(street) and self._kw('Get Property', street, 'value') == inputs['address']['street']:
                raise AssertionError('Another account can read the owner street value.')
            self._capture([case['business_id']], 'foreign-address-view')
            self._kw('Go To', self.base + delete)
            self._capture([case['business_id']], 'foreign-address-delete')
            self._logout()
            self._extra_login(inputs['account'])
            self._extra_account()
            self._extra_book()
            self._kw('Click', 'css=.user-account-address a[href=' + json.dumps(edit) + ']')
            self._extra_address_values(inputs, title)
        self._extra_delete_address(edit, delete)

    def _extra_password_page(self):
        """Reach Change password through account details and its native link."""
        self._extra_account()
        self._kw('Click', 'css=.user-account a[href="/customer/change-password/"]')

    def _extra_password_submit(self, old, new, confirmation):
        """Use secret entry for each literal password and the first visible save button."""
        for name, value in [('old_password', old), ('new_password1', new), ('new_password2', confirmation)]:
            key = 'ROBOT_EXTRA_' + name.upper()
            os.environ[key] = value
            self._secret('css=input[name="' + name + '"]', key)
        self._kw('Click', 'css=form:has(input[name="old_password"]) .btn-toolbar button[type="submit"] >> nth=0')

    def _extra_restore_password(self, inputs):
        """Restore the dedicated fixture through a fresh UI session and verify original access."""
        self._kw('New Context', 'viewport={"width": 1440, "height": 1000}')
        self._kw('New Page', self.base + '/')
        self._extra_login(dict(inputs['account'], password=inputs['new_password']))
        self._extra_password_page()
        self._extra_password_submit(inputs['new_password'], inputs['account']['password'], inputs['account']['password'])
        self._kw('Wait For Elements State', 'css=.alert-success', 'visible')
        self._logout()
        self._extra_login(inputs['account'])

    def _password_change(self, case):
        """Observe validation and genuine old/new authentication, restoring via UI after success."""
        inputs = case['inputs']
        self._extra_login(inputs['account'])
        self._extra_password_page()
        if case['expected'] == 'login_required':
            url = self._kw('Get Url')
            self._logout()
            self._kw('Go To', url)
            self._kw('Wait For Elements State', 'css=form[action="/login/"] input[name="username"]', 'visible')
            if self._count('css=input[name="old_password"]') or '/login/' not in self._kw('Get Url'):
                raise AssertionError('Signed-out access exposed the password-change form.')
            return
        if case['expected'] == 'rejected':
            self._extra_password_submit(inputs['old_password'], inputs['new_password'], inputs['confirm_password'])
            field = 'old_password' if not inputs['old_password'] or inputs['old_password'] != inputs['account']['password'] else 'new_password1' if not inputs['new_password'] else 'new_password2'
            self._until(lambda: self._visible('css=.has-error, .errorlist') or not self._read('css=input[name="' + field + '"]', '(el) => el.checkValidity()'), 'password validation on the changed field')
            self._capture([case['business_id']], 'password-validation')
            self._logout()
            self._extra_login(inputs['account'])
            return
        changed = True
        try:
            self._extra_password_submit(inputs['old_password'], inputs['new_password'], inputs['confirm_password'])
            self._kw('Wait For Elements State', 'css=.alert-success', 'visible')
            self._capture([case['business_id']], 'password-changed')
            self._logout()
            self._login(inputs['account']['username'], inputs['account']['password'])
            self._until(lambda: self._visible('css=.alert-danger, .has-error'), 'old-password rejection')
            if self._count('css=.top-nav a[href*="/logout/"]'):
                raise AssertionError('The old password still authenticates after the change.')
            self._capture([case['business_id']], 'old-password-rejected')
            self._extra_restore_password(inputs)
            changed = False
            self._capture([case['business_id']], 'original-password-restored')
        except Exception:
            self._capture([case['business_id']], 'password-failure-before-recovery', role='failure')
            if changed:
                try:
                    self._extra_restore_password(inputs)
                except Exception:
                    self.robot.log('UI password recovery failed. The dedicated fixture may retain the reviewed new password; inspect evidence and restore it through the UI before rerunning. Setup preserves existing credentials.', 'WARN')
            raise

*** Settings ***
Library             Browser
Library             OperatingSystem
Library             AccountSecrets.py
Library             /fuzcake-data/fuzcake_data/robot_data.py
Test Setup          Open Storefront
Test Teardown       Close Browser
Test Tags           smoke

*** Variables ***
${BASE_URL}                 %{BASE_URL=http://127.0.0.1:65535}
${CHROMIUM_EXECUTABLE}      ${None}

*** Test Cases ***
Customer Finds Product And Updates Basket
    Click    css=article.product_pod h3 a[title="Rose Nocturne"]
    Get Text    css=h1    ==    Rose Nocturne
    Click    css=button[type="submit"]:has-text("Add to basket")
    Click    css=a:has-text("View basket") >> nth=0
    Fill Text    css=input[name="form-0-quantity"]    2
    Click    css=button:has-text("Update") >> nth=0
    Get Property    css=input[name="form-0-quantity"]    value    ==    2
    Get Text    body    contains    Rose Nocturne

Customer Uses A Voucher Through Basket
    Add Fragrance To Basket
    Click    css=#voucher_form_link a
    Fill Text    css=#id_code    OSCAR10
    Click    css=#voucher_form button[type="submit"]
    Get Text    body    contains    OSCAR10
    Get Text    body    contains    discount

Customer Places Order And Opens Order History
    Log In As    CUSTOMER
    Add Fragrance To Basket
    Click    css=a:has-text("Proceed to checkout")
    Fill Shipping Address
    Click    css=#view_preview
    Get Text    body    contains    Rose Nocturne
    Click    css=#place-order
    Get Text    body    contains    confirmation
    Click    css=a:has-text("Continue shopping")
    Click    css=#top_page a:has-text("Account")
    Click    css=a:has-text("Order History")
    Get Element Count    css=table tbody tr    >=    1

Admin Opens Orders And Catalogue From Dashboard
    Log In As    ADMIN
    Click    css=#top_page a:has-text("Dashboard")
    Click    css=a.dropdown-toggle:has-text("Fulfilment")
    Click    css=a:has-text("Orders") >> nth=0
    Get Text    css=h1    contains    Orders
    Click    css=a.dropdown-toggle:has-text("Catalogue")
    Click    css=a:has-text("Products") >> nth=0
    Get Text    body    contains    Rose Nocturne

Seller Opens Assigned Products
    Log In As    SELLER
    Click    css=#top_page a:has-text("Dashboard")
    Click    css=a.dropdown-toggle:has-text("Catalogue")
    Click    css=a:has-text("Products") >> nth=0
    Get Text    body    contains    Rose Nocturne
    Get Text    body    contains    Jasmine Tide

*** Keywords ***
Open Storefront
    New Browser    chromium    headless=${TRUE}    executablePath=${CHROMIUM_EXECUTABLE}
    New Context    locale=en-GB    viewport={'width': 1440, 'height': 1000}
    New Page    ${BASE_URL}
    Get Text    body    contains    fuzcake

Log In As
    [Arguments]    ${role}
    Click    css=#login_link
    ${email}=    Get Environment Variable    ROBOT_${role}_EMAIL
    Fill Text    css=#id_login-username    ${email}
    Enter Account Password    ${role}    css=#id_login-password
    Click    css=button[name="login_submit"]
    IF    '${role}' == 'ADMIN'
        Get Element States    css=#logout_form    contains    visible
        Click    css=a:has-text("Return to site")
    END
    Get Element States    css=#logout_link    contains    visible

Add Fragrance To Basket
    Click    css=article.product_pod h3 a[title="Rose Nocturne"]
    Click    css=button[type="submit"]:has-text("Add to basket")
    Click    css=a:has-text("View basket") >> nth=0

Fill Shipping Address
    ${address}=    Get Shipping Address
    Fill Text    css=#id_first_name    ${address}[first_name]
    Fill Text    css=#id_last_name    ${address}[last_name]
    Fill Text    css=#id_line1    ${address}[street]
    Fill Text    css=#id_line4    ${address}[city]
    Fill Text    css=#id_postcode    ${address}[postal_code]
    Select Options By    css=#id_country    value    ${address}[country]
    Click    css=#new_shipping_address button[type="submit"]

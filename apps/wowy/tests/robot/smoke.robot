*** Settings ***
Library             Browser
Library             OperatingSystem
Library             AccountSecrets.py
Test Teardown       Close Browser
Test Tags           smoke

*** Variables ***
${BASE_URL}          %{BASE_URL=http://127.0.0.1:65535}

*** Test Cases ***
Customer Places A Local Order Through Store Navigation
    New Browser    chromium    headless=${True}
    New Context
    New Page    ${BASE_URL}/
    Click    css=a:has-text("Log in") >> nth=0
    Fill Text    css=input[name="email"]    %{ROBOT_CUSTOMER_EMAIL}
    Enter Account Password    CUSTOMER    css=input[name="password"]
    Click    css=button[type="submit"]
    Click    css=a:has-text("Floral & romantic") >> nth=0
    Click    css=a:has-text("Rose Nocturne") >> nth=0
    Click    css=.add-cart-btn, .add-to-cart-btn >> nth=0
    Wait For Elements State    css=.wowy-notification    hidden    timeout=10s
    Click    css=a:has-text("Checkout") >> nth=0
    Get Text    body    contains    Rose Nocturne
    Click    css=button[type="submit"]:has-text("Place order")
    Get Text    body    contains    FC-
    Click    css=a:has-text("My orders") >> nth=0
    Get Text    body    contains    Rose Nocturne

Administrator Reaches Native Product Management
    New Browser    chromium    headless=${True}
    New Context
    New Page    ${BASE_URL}/
    Click    css=a:has-text("Log in") >> nth=0
    Fill Text    css=input[name="email"]    %{ROBOT_ADMIN_EMAIL}
    Enter Account Password    ADMIN    css=input[name="password"]
    Click    css=button[type="submit"]
    Click    css=a:has-text("Administration") >> nth=0
    Click    css=a:has-text("Products") >> nth=0
    Click    css=a:has-text("All Products") >> nth=0
    Get Text    body    contains    Products

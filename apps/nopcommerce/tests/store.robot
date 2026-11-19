*** Settings ***
Library    Browser
Suite Teardown    Close Browser

*** Test Cases ***
Native Storefront Opens With Shared Catalogue
    New Browser    chromium    headless=True
    New Context
    # Share the app network namespace to keep native loopback redirects valid.
    New Page    %{BASE_URL}
    Get Text    body    contains    Rose Nocturne
    Get Element Count    img    >    0


*** Settings ***
Library             Browser
Library             AccountSecrets.py
Test Teardown       Close Browser
Test Tags           smoke

*** Variables ***
${BASE_URL}          %{BASE_URL=http://127.0.0.1:65535}

*** Test Cases ***
Customer Opens A Seeded Product Through The Catalogue
    New Browser    chromium    headless=${True}
    New Context
    New Page    ${BASE_URL}/
    Click    css=a:has-text("Floral & romantic") >> nth=0
    Click    css=a:has-text("Rose Nocturne") >> nth=0
    Get Text    body    contains    Rose Nocturne
    Get Element States    css=.btn-add-to-cart button[type="submit"]    contains    enabled

Administrator Logs In Through The Native Form
    New Browser    chromium    headless=${True}
    New Context
    New Page    ${BASE_URL}/sa/
    Fill Text    css=input[name="username"]    %{ROBOT_ADMIN_EMAIL}
    Enter Account Password    ADMIN    css=input[name="password"]
    Click    css=button[type="submit"]
    Get Text    body    contains    Dashboard

Catalogue List Keeps Readable Columns And Keyboard Focus
    New Browser    chromium    headless=${True}
    New Context    viewport={"width": 1440, "height": 1000}
    New Page    ${BASE_URL}/
    Click    css=.fc-menu a:has-text("The collection")
    ${pointer_focus}=    Evaluate JavaScript    css=.fc-menu a:has-text("The collection")    (el) => !el.matches(':focus-visible') && getComputedStyle(el).outlineStyle === 'none'
    Should Be True    ${pointer_focus}
    Press Keys    css=body    Tab
    ${keyboard_focus}=    Evaluate JavaScript    css=body    () => document.activeElement.matches(':focus-visible') && getComputedStyle(document.activeElement).outlineStyle !== 'none'
    Should Be True    ${keyboard_focus}
    Click    css=label[for="product-list-view-type"]
    ${readable_list}=    Evaluate JavaScript    css=.product-list-view .product-card >> nth=0    (el) => { const image = el.querySelector('.image-wrap').getBoundingClientRect(); const detail = el.querySelector('.detail-wrap').getBoundingClientRect(); const name = el.querySelector('.name').getBoundingClientRect(); return image.width > 120 && image.height > 120 && detail.left >= image.right - 1 && detail.width > 250 && name.width > 200 && el.getBoundingClientRect().height < 650; }
    Should Be True    ${readable_list}
    Click    css=#login-dropdown > a
    ${readable_login}=    Evaluate JavaScript    css=#login-dropdown .control-label >> nth=0    (el) => getComputedStyle(el).color === getComputedStyle(document.body).color
    Should Be True    ${readable_login}
    Click    css=#login-dropdown > a
    Click    css=.product-list-view .product-card .actions button >> nth=0
    Wait For Elements State    css=.product-preview-modal.in    visible
    ${preview_price}=    Evaluate JavaScript    css=.product-preview-modal .price-line >> nth=0    (el) => getComputedStyle(el).color === getComputedStyle(document.documentElement).getPropertyValue('--fc-color-accent').trim() || getComputedStyle(el).color === 'rgb(125, 68, 62)'
    Should Be True    ${preview_price}

*** Settings ***
Library             Browser
Test Setup          Open Isolated Browser
Test Teardown       Close Browser
Test Tags           smoke

*** Variables ***
${BASE_URL}          %{BASE_URL=http://pretix.localhost:1}

*** Test Cases ***
Customer Opens Event From Organizer List
    New Page    ${BASE_URL}/demo-organizer/
    Click    a:has-text("Future Makers Summit")
    Get Text    body    contains    Community ticket
    Get Text    body    contains    Standard ticket
    Get Element States    css=#btn-add-to-cart    contains    visible

Customer Adds A Free Ticket Through The Interface
    New Page    ${BASE_URL}/demo-organizer/
    Click    a:has-text("Future Makers Summit")
    Select Options By    css=article:has-text("Community ticket") select[name^="item_"]    value    1
    Click    css=#btn-add-to-cart
    Get Text    css=.cart    contains    Community ticket

Admin Opens Password Recovery From Login
    New Page    ${BASE_URL}/control/
    Get Element States    css=input[name="email"]    contains    visible
    Click    a:has-text("Lost password?")
    Get Element States    css=input[name="email"]    contains    visible
    Get Url    contains    forgot

Admin Logs In Through The Interface
    New Page    ${BASE_URL}/control/
    Fill Text    css=input[name="email"]    %{ADMIN_EMAIL=admin@example.test}
    Fill Secret    css=input[name="password"]    %ADMIN_PASSWORD
    Click    css=button[type="submit"]
    Get Text    body    contains    Future Makers Summit

*** Keywords ***
Open Isolated Browser
    ${gateway_ip}=    Evaluate    socket.gethostbyname("gateway")    modules=socket
    ${launch_args}=    Create List    --host-resolver-rules=MAP pretix.localhost ${gateway_ip}:18445
    New Browser    chromium    headless=${TRUE}    args=${launch_args}
    New Context    locale=en-GB

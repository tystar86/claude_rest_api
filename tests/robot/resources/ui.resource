*** Settings ***
Library    Browser
Resource   common.resource

*** Keywords ***
Open App Browser
    New Browser    browser=${BROWSER}    headless=true
    New Context
    New Page    ${UI_BASE_URL}

Close App Browser
    Close Browser

Login In Browser As Moderator
    Go To    ${UI_BASE_URL}/login
    Wait For Elements State    css=input[name="email"]       visible    10s
    Fill Text    css=input[name="email"]       ${MOD_EMAIL}
    Fill Text    css=input[name="password"]    ${MOD_PASSWORD}
    Click    css=button[type="submit"]
    Wait For Elements State    css=input[name="email"]    detached    10s

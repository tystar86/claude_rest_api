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

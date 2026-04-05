*** Settings ***
Documentation    UI tests for the Tags page.
Resource         ../resources/ui.resource
Resource         ../resources/api.resource
Suite Setup      Run Keywords
...              Create API Session    AND
...              Open App Browser
Suite Teardown   Close App Browser

*** Variables ***
${TAGS_URL}    ${UI_BASE_URL}/tags

*** Test Cases ***
Tags Page Loads For Anonymous User
    Go To    ${TAGS_URL}
    Wait For Elements State    css=.nb-tag-grid    visible    10s

New Tag Button Not Visible When Logged Out
    Go To    ${TAGS_URL}
    Wait For Elements State    css=.nb-tag-grid    visible    10s
    Get Element Count    text=New Tag    ==    0

New Tag Button Visible When Logged In As Moderator
    Login In Browser As Moderator
    Go To    ${TAGS_URL}
    Wait For Elements State    css=.nb-tag-grid    visible    10s
    Wait For Elements State    text=New Tag    visible    5s

Create Tag Form Appears On Button Click
    Login In Browser As Moderator
    Go To    ${TAGS_URL}
    Wait For Elements State    text=New Tag    visible    10s
    Click    text=New Tag
    Wait For Elements State    css=input[placeholder="Tag name (lowercase)"]    visible    5s

Tag Input Accepts Lowercase Only
    Login In Browser As Moderator
    Go To    ${TAGS_URL}
    Wait For Elements State    text=New Tag    visible    10s
    Click    text=New Tag
    Wait For Elements State    css=input[placeholder="Tag name (lowercase)"]    visible    5s
    Fill Text    css=input[placeholder="Tag name (lowercase)"]    UPPERCASE
    ${value}=    Get Property    css=input[placeholder="Tag name (lowercase)"]    value
    Should Be Equal    ${value}    uppercase

Created Tag Appears In Tag List
    Login As Moderator
    ${ts}=    Get Time    epoch
    ${tag_name}=    Set Variable    ui-robot-tag-${ts}
    Create Tag Via API    ${tag_name}
    Go To    ${TAGS_URL}
    Wait For Elements State    text=${tag_name}    visible    10s

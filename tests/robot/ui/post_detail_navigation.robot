*** Settings ***
Documentation    UI tests for PostDetail quick navigation.
Resource         ../resources/ui.resource
Suite Setup      Open App Browser
Suite Teardown   Close App Browser

*** Test Cases ***
Posts Page Loads
    Go To    ${UI_BASE_URL}/posts
    Wait For Elements State    text=total    visible    10s

Post Detail Quick Nav Buttons Visible
    [Documentation]    Requires at least one post in the environment.
    Go To    ${UI_BASE_URL}/posts
    Wait For Elements State    css=ul.list-unstyled li a    visible    10s
    Click    css=ul.list-unstyled li a
    Wait For Elements State    text=Comments    visible    10s
    Wait For Elements State    role=button[name="Top"]    visible
    Wait For Elements State    role=button[name="Comments"]    visible
    Wait For Elements State    role=button[name="Bottom"]    visible

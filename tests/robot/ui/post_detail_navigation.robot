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
    ...    Quick-nav buttons (Top/Comments/Bottom) only render when the page is
    ...    scrollable (scrollHeight > innerHeight + 80). After navigation we
    ...    force scrollability via JS so the assertion is deterministic regardless
    ...    of how long the clicked post's content is.
    Go To    ${UI_BASE_URL}/posts
    Wait For Elements State    css=ul.list-unstyled li a    visible    10s
    Click    css=ul.list-unstyled li a
    Wait For Elements State    text=Comments    visible    10s
    # Guarantee the page is scrollable so React renders the quick-nav buttons
    Evaluate JavaScript    NONE
    ...    document.body.style.minHeight = "200vh";
    ...    window.dispatchEvent(new Event("resize"));
    Wait For Elements State    role=button[name="Top"]       visible    5s
    Wait For Elements State    role=button[name="Comments"]  visible    5s
    Wait For Elements State    role=button[name="Bottom"]    visible    5s

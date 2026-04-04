*** Settings ***
Documentation    UI tests for PostDetail quick navigation.
Resource         ../resources/ui.resource
Resource         ../resources/api.resource
Suite Setup      Run Keywords
...              Create API Session    AND
...              Login As Moderator    AND
...              Create Published Post Via API    Robot Nav Test Post    This is a robot test post body for navigation testing.    AND
...              Open App Browser
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
    Wait For Elements State    css=ul.list-unstyled li a >> nth=0    visible    10s
    Click    css=ul.list-unstyled li a >> nth=0
    Wait For Elements State    css=#comments-section    visible    10s
    # Guarantee the page is scrollable so React renders the quick-nav buttons
    Evaluate JavaScript    ${NONE}    document.body.style.minHeight = "200vh"; window.scrollBy(0, 1);
    Wait For Elements State    css=button[aria-label="Scroll to top"]      visible    5s
    Wait For Elements State    css=button[aria-label="Scroll to comments"]  visible    5s
    Wait For Elements State    css=button[aria-label="Scroll to bottom"]    visible    5s

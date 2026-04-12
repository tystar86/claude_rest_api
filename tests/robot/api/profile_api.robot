*** Settings ***
Documentation    API tests for user registration and profile management.
Resource         ../resources/api.resource
Suite Setup      Run Keywords    Create API Session    AND    Ensure Moderator User

*** Test Cases ***
# ── Registration ──────────────────────────────────────────────────────────────

Register Creates User And Returns 201
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}
    ${ts}=    Evaluate    __import__('time').time()
    ${email}=    Set Variable    robot-reg-${ts}@example.com
    ${username}=    Set Variable    robotreg${ts}
    ${payload}=    Create Dictionary    email=${email}    username=${username}    password=robotpass123
    ${resp}=    POST On Session    api    /api/auth/register/    json=${payload}    headers=${headers}
    Should Be Equal As Integers    ${resp.status_code}    201
    ${json}=    Set Variable    ${resp.json()}
    Dictionary Should Contain Key    ${json}    username

Duplicate Registration Returns 400 With Generic Detail
    Register Test User
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}
    ${payload}=    Create Dictionary
    ...    email=${TEST_EMAIL}
    ...    username=${TEST_USERNAME}
    ...    password=${TEST_PASSWORD}
    ${resp}=    POST On Session    api    /api/auth/register/    json=${payload}    headers=${headers}    expected_status=any
    Should Be Equal As Integers    ${resp.status_code}    400
    Should Be Equal    ${resp.json()["detail"]}    Registration failed.

# ── Profile Update ────────────────────────────────────────────────────────────

Profile Update Requires Authentication
    [Setup]    Create API Session
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}    Content-Type=application/json
    ${payload}=    Create Dictionary    username=hacker
    ${resp}=    PATCH On Session
    ...    api
    ...    /api/auth/profile/
    ...    json=${payload}
    ...    headers=${headers}
    ...    expected_status=any
    Should Be Equal As Integers    ${resp.status_code}    401

Moderator Can Update Username
    Login As Moderator
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}    Content-Type=application/json
    ${payload}=    Create Dictionary    username=${MOD_USERNAME}
    ${resp}=    PATCH On Session
    ...    api
    ...    /api/auth/profile/
    ...    json=${payload}
    ...    headers=${headers}
    Should Be Equal As Integers    ${resp.status_code}    200
    ${json}=    Set Variable    ${resp.json()}
    Should Be Equal    ${json["username"]}    ${MOD_USERNAME}
    Dictionary Should Contain Key    ${json}    profile

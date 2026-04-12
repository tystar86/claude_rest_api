*** Settings ***
Documentation    API tests for Ninja auth endpoints: CSRF, login, logout, current user, profile.
Resource         ../resources/api.resource
Suite Setup      Run Keywords    Create API Session    AND    Ensure Moderator User

*** Test Cases ***
# ── CSRF ──────────────────────────────────────────────────────────────────────

CSRF Endpoint Returns Token In Body And Cookie
    ${resp}=    GET On Session    api    /api/auth/csrf/
    Should Be Equal As Integers    ${resp.status_code}    200
    ${json}=    Set Variable    ${resp.json()}
    Dictionary Should Contain Key    ${json}    csrfToken
    Should Not Be Empty    ${json["csrfToken"]}
    Dictionary Should Contain Key    ${resp.cookies}    csrftoken

# ── Login ─────────────────────────────────────────────────────────────────────

Login With Valid Credentials Returns User Payload
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}
    ${payload}=    Create Dictionary    email=${MOD_EMAIL}    password=${MOD_PASSWORD}
    ${resp}=    POST On Session    api    /api/auth/login/    json=${payload}    headers=${headers}
    Should Be Equal As Integers    ${resp.status_code}    200
    ${json}=    Set Variable    ${resp.json()}
    Dictionary Should Contain Key    ${json}    username
    Dictionary Should Contain Key    ${json}    email
    Dictionary Should Contain Key    ${json}    profile

Login With Bad Password Returns 400
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}
    ${payload}=    Create Dictionary    email=${MOD_EMAIL}    password=wrong-password
    ${resp}=    POST On Session    api    /api/auth/login/    json=${payload}    headers=${headers}    expected_status=any
    Should Be Equal As Integers    ${resp.status_code}    400
    Should Be Equal    ${resp.json()["detail"]}    Invalid credentials.

Login GET Returns 405 With Allow Header
    ${resp}=    GET On Session    api    /api/auth/login/    expected_status=any
    Should Be Equal As Integers    ${resp.status_code}    405
    ${json}=    Set Variable    ${resp.json()}
    Should Be Equal    ${json["detail"]}    Method not allowed.
    ${allow}=    Get From Dictionary    ${resp.headers}    Allow
    Should Contain    ${allow}    POST

# ── Current User ──────────────────────────────────────────────────────────────

Current User Requires Authentication
    [Setup]    Create API Session
    ${resp}=    GET On Session    api    /api/auth/user/    expected_status=any
    Should Be Equal As Integers    ${resp.status_code}    403

Current User Returns Payload When Logged In
    Login As Moderator
    ${resp}=    GET On Session    api    /api/auth/user/
    Should Be Equal As Integers    ${resp.status_code}    200
    ${json}=    Set Variable    ${resp.json()}
    Dictionary Should Contain Key    ${json}    username
    Dictionary Should Contain Key    ${json}    email
    Dictionary Should Contain Key    ${json}    profile
    Dictionary Should Contain Key    ${json}    can_manage_tags

# ── Logout ────────────────────────────────────────────────────────────────────

Logout Requires Authentication
    [Setup]    Create API Session
    ${resp}=    POST On Session    api    /api/auth/logout/    expected_status=any
    Should Be Equal As Integers    ${resp.status_code}    403

Logout Succeeds When Authenticated
    Login As Moderator
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}
    ${resp}=    POST On Session    api    /api/auth/logout/    headers=${headers}
    Should Be Equal As Integers    ${resp.status_code}    200
    Should Be Equal    ${resp.json()["detail"]}    Logged out.
    ${after}=    GET On Session    api    /api/auth/user/    expected_status=any
    Should Be Equal As Integers    ${after.status_code}    403

# ── HEAD fallback ─────────────────────────────────────────────────────────────

HEAD On Post List Mirrors GET Status
    ${head}=    HEAD On Session    api    /api/posts/
    Should Be Equal As Integers    ${head.status_code}    200

HEAD On Dashboard Mirrors GET Status
    ${head}=    HEAD On Session    api    /api/dashboard/
    Should Be Equal As Integers    ${head.status_code}    200

# ── 405 Method Not Allowed ────────────────────────────────────────────────────

Register GET Returns 405
    ${resp}=    GET On Session    api    /api/auth/register/    expected_status=any
    Should Be Equal As Integers    ${resp.status_code}    405
    Should Be Equal    ${resp.json()["detail"]}    Method not allowed.

Tags DELETE Without Slug Returns 405
    Login As Moderator
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}
    ${resp}=    DELETE On Session    api    /api/tags/    headers=${headers}    expected_status=any
    Should Be Equal As Integers    ${resp.status_code}    405

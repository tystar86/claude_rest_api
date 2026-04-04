*** Settings ***
Library    RequestsLibrary
Library    Collections
Resource   common.resource

*** Keywords ***
Create API Session
    Create Session    api    ${API_BASE_URL}

Get CSRF Token
    ${resp}=    GET On Session    api    /api/auth/csrf/
    Should Be Equal As Integers    ${resp.status_code}    200
    ${token}=    Get From Dictionary    ${resp.cookies}    csrftoken
    RETURN    ${token}

Register Test User
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}
    ${payload}=    Create Dictionary
    ...    email=${TEST_EMAIL}
    ...    username=${TEST_USERNAME}
    ...    password=${TEST_PASSWORD}
    ${resp}=    POST On Session
    ...    api
    ...    /api/auth/register/
    ...    json=${payload}
    ...    headers=${headers}
    ...    expected_status=any
    IF    ${resp.status_code} == 400
        ${detail}=    Get From Dictionary    ${resp.json()}    detail
        Should Be Equal As Strings    ${detail}    Registration failed.
    ELSE
        Should Be Equal As Integers    ${resp.status_code}    201
    END

Login Test User
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}
    ${payload}=    Create Dictionary    email=${TEST_EMAIL}    password=${TEST_PASSWORD}
    ${resp}=    POST On Session
    ...    api
    ...    /api/auth/login/
    ...    json=${payload}
    ...    headers=${headers}
    ...    expected_status=any
    Should Be Equal As Integers    ${resp.status_code}    200

Create Tag Via API
    [Arguments]    ${name}
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}
    ${payload}=    Create Dictionary    name=${name}
    ${resp}=    POST On Session
    ...    api
    ...    /api/tags/
    ...    json=${payload}
    ...    headers=${headers}
    Should Be Equal As Integers    ${resp.status_code}    201
    ${data}=    Set Variable    ${resp.json()}
    RETURN    ${data}

Create Post Via API
    [Arguments]    ${title}    ${body}
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}
    ${payload}=    Create Dictionary    title=${title}    body=${body}    status=draft
    ${resp}=    POST On Session
    ...    api
    ...    /api/posts/
    ...    json=${payload}
    ...    headers=${headers}
    Should Be Equal As Integers    ${resp.status_code}    201
    ${data}=    Set Variable    ${resp.json()}
    RETURN    ${data}

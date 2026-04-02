*** Settings ***
Documentation    API smoke tests for tag endpoints.
Resource         ../resources/api.resource
Suite Setup      Create API Session
Test Setup       Register Test User

*** Test Cases ***
Tag List Returns 200 For Anonymous
    ${resp}=    GET On Session    api    /api/tags/
    Should Be Equal As Integers    ${resp.status_code}    200
    ${json}=    Set Variable    ${resp.json()}
    Dictionary Should Contain Key    ${json}    results
    Dictionary Should Contain Key    ${json}    count
    Dictionary Should Contain Key    ${json}    total_pages

Authenticated User Can Create Tag
    Login Test User
    ${tag}=    Create Tag Via API    robot-tag
    Dictionary Should Contain Key    ${tag}    slug
    Should Be Equal    ${tag["name"]}    robot-tag

Tag Name Is Stored Lowercase
    Login Test User
    ${tag}=    Create Tag Via API    RobotUpperTag
    Should Be Equal    ${tag["name"]}    robotuppertag

Mixed Case Tag Name Is Normalised
    Login Test User
    ${tag}=    Create Tag Via API    RoBOt-MiXeD
    Should Be Equal    ${tag["name"]}    robot-mixed

Anonymous User Cannot Create Tag
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}
    ${payload}=    Create Dictionary    name=anon-tag
    ${resp}=    POST On Session
    ...    api
    ...    /api/tags/
    ...    json=${payload}
    ...    headers=${headers}
    ...    expected_status=any
    Should Be Equal As Integers    ${resp.status_code}    403

Duplicate Tag Name Returns 400
    Login Test User
    Create Tag Via API    unique-tag-dupe
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}
    ${payload}=    Create Dictionary    name=unique-tag-dupe
    ${resp}=    POST On Session
    ...    api
    ...    /api/tags/
    ...    json=${payload}
    ...    headers=${headers}
    ...    expected_status=any
    Should Be Equal As Integers    ${resp.status_code}    400
    ${json}=    Set Variable    ${resp.json()}
    Should Be Equal    ${json["detail"]}    Tag name already exists.

Duplicate Check Is Case Insensitive
    Login Test User
    Create Tag Via API    case-check-tag
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}
    ${payload}=    Create Dictionary    name=CASE-CHECK-TAG
    ${resp}=    POST On Session
    ...    api
    ...    /api/tags/
    ...    json=${payload}
    ...    headers=${headers}
    ...    expected_status=any
    Should Be Equal As Integers    ${resp.status_code}    400

Empty Tag Name Returns 400
    Login Test User
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}
    ${payload}=    Create Dictionary    name=${EMPTY}
    ${resp}=    POST On Session
    ...    api
    ...    /api/tags/
    ...    json=${payload}
    ...    headers=${headers}
    ...    expected_status=any
    Should Be Equal As Integers    ${resp.status_code}    400

Created Tag Appears In Tag List
    Login Test User
    ${tag}=    Create Tag Via API    listed-tag
    ${resp}=    GET On Session    api    /api/tags/
    ${json}=    Set Variable    ${resp.json()}
    ${names}=    Evaluate    [t["name"] for t in $json["results"]]
    List Should Contain Value    ${names}    listed-tag

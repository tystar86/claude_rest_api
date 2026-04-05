*** Settings ***
Documentation    API smoke tests for blog endpoints.
Resource         ../resources/api.resource
Suite Setup      Create API Session
Test Setup       Register Test User

*** Test Cases ***
Dashboard Endpoint Returns Stats
    ${resp}=    GET On Session    api    /api/dashboard/
    Should Be Equal As Integers    ${resp.status_code}    200
    ${json}=    Set Variable    ${resp.json()}
    Dictionary Should Contain Key    ${json}    stats

Can Create Post As Authenticated User
    Login Test User
    ${post}=    Create Post Via API    Robot API Post    This post was created by Robot Framework.
    Dictionary Should Contain Key    ${post}    slug
    Should Be Equal    ${post["title"]}    Robot API Post

Post List Returns Paginated Payload
    ${resp}=    GET On Session    api    /api/posts/
    Should Be Equal As Integers    ${resp.status_code}    200
    ${json}=    Set Variable    ${resp.json()}
    Dictionary Should Contain Key    ${json}    results
    Dictionary Should Contain Key    ${json}    total_pages

Post List Pagination Returns Correct Structure
    ${resp}=    GET On Session    api    /api/posts/
    Should Be Equal As Integers    ${resp.status_code}    200
    ${json}=    Set Variable    ${resp.json()}
    Dictionary Should Contain Key    ${json}    count
    Dictionary Should Contain Key    ${json}    total_pages
    Dictionary Should Contain Key    ${json}    page
    Dictionary Should Contain Key    ${json}    results
    ${count}=    Get From Dictionary    ${json}    count
    Should Be True    ${count} >= 0

Post List Page Two Is Accessible
    ${resp}=    GET On Session    api    /api/posts/?page=2
    Should Be Equal As Integers    ${resp.status_code}    200
    ${json}=    Set Variable    ${resp.json()}
    ${page}=    Get From Dictionary    ${json}    page
    Should Be Equal As Integers    ${page}    2

Post List Invalid Page Returns Safe Response
    ${resp}=    GET On Session    api    /api/posts/?page=abc
    Should Not Be Equal As Integers    ${resp.status_code}    500
    ${resp2}=    GET On Session    api    /api/posts/?page=-1
    Should Not Be Equal As Integers    ${resp2.status_code}    500

Post List Large Page Number Returns Safe Response
    ${resp}=    GET On Session    api    /api/posts/?page=999999
    Should Not Be Equal As Integers    ${resp.status_code}    500
    ${json}=    Set Variable    ${resp.json()}
    Dictionary Should Contain Key    ${json}    results

Post Detail Returns Correct Fields
    ${resp}=    GET On Session    api    /api/posts/
    ${json}=    Set Variable    ${resp.json()}
    ${results}=    Get From Dictionary    ${json}    results
    ${length}=    Get Length    ${results}
    IF    ${length} > 0
        ${first}=    Get From List    ${results}    0
        Dictionary Should Contain Key    ${first}    slug
        Dictionary Should Contain Key    ${first}    title
        Dictionary Should Contain Key    ${first}    author
        Dictionary Should Contain Key    ${first}    comment_count
    END

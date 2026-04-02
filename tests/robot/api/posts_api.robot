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

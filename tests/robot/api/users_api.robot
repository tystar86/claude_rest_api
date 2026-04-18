*** Settings ***
Documentation    API smoke tests for users endpoint with large dataset.
Resource         ../resources/api.resource
Suite Setup      Create API Session

*** Test Cases ***
User List Returns Paginated Response
    ${resp}=    GET On Session    api    /api/users/
    Should Be Equal As Integers    ${resp.status_code}    200
    ${json}=    Set Variable    ${resp.json()}
    Dictionary Should Contain Key    ${json}    count
    Dictionary Should Contain Key    ${json}    total_pages
    Dictionary Should Contain Key    ${json}    results

User List Count Reflects Dataset Size
    ${resp}=    GET On Session    api    /api/users/
    ${json}=    Set Variable    ${resp.json()}
    ${count}=    Get From Dictionary    ${json}    count
    Should Be True    ${count} >= 0

User List Results Have Required Fields
    ${resp}=    GET On Session    api    /api/users/
    ${json}=    Set Variable    ${resp.json()}
    ${results}=    Get From Dictionary    ${json}    results
    ${length}=    Get Length    ${results}
    IF    ${length} > 0
        ${first}=    Get From List    ${results}    0
        Dictionary Should Contain Key    ${first}    id
        Dictionary Should Contain Key    ${first}    username
        Dictionary Should Contain Key    ${first}    post_count
        Dictionary Should Contain Key    ${first}    profile
    END

User List Pagination Works
    ${resp}=    GET On Session    api    /api/users/    params=page=2
    Should Not Be Equal As Integers    ${resp.status_code}    500

Dashboard Stats Are Present And Numeric
    ${resp}=    GET On Session    api    /api/dashboard/
    Should Be Equal As Integers    ${resp.status_code}    200
    ${json}=    Set Variable    ${resp.json()}
    ${stats}=    Get From Dictionary    ${json}    stats
    Dictionary Should Contain Key    ${stats}    total_posts
    Dictionary Should Contain Key    ${stats}    comments
    Dictionary Should Contain Key    ${stats}    authors
    Dictionary Should Contain Key    ${stats}    active_tags
    Dictionary Should Contain Key    ${stats}    new_posts_7d
    ${total}=    Get From Dictionary    ${stats}    total_posts
    Should Be True    ${total} >= 0

Dashboard Returns Latest Posts And Tags
    ${resp}=    GET On Session    api    /api/dashboard/
    ${json}=    Set Variable    ${resp.json()}
    Dictionary Should Contain Key    ${json}    activity
    Dictionary Should Contain Key    ${json}    latest_posts
    Dictionary Should Contain Key    ${json}    most_liked_posts
    Dictionary Should Contain Key    ${json}    most_used_tags
    Dictionary Should Contain Key    ${json}    top_authors

*** Settings ***
Documentation    API smoke tests for comments endpoint.
Resource         ../resources/api.resource
Suite Setup      Create API Session
Test Setup       Register Test User

*** Test Cases ***
Comment List Returns Paginated Response
    ${resp}=    GET On Session    api    /api/comments/
    Should Be Equal As Integers    ${resp.status_code}    200
    ${json}=    Set Variable    ${resp.json()}
    Dictionary Should Contain Key    ${json}    count
    Dictionary Should Contain Key    ${json}    total_pages
    Dictionary Should Contain Key    ${json}    results

Comment List Results Have Required Fields
    ${resp}=    GET On Session    api    /api/comments/
    ${json}=    Set Variable    ${resp.json()}
    ${results}=    Get From Dictionary    ${json}    results
    ${length}=    Get Length    ${results}
    IF    ${length} > 0
        ${first}=    Get From List    ${results}    0
        Dictionary Should Contain Key    ${first}    id
        Dictionary Should Contain Key    ${first}    author
        Dictionary Should Contain Key    ${first}    body
        Dictionary Should Contain Key    ${first}    post_title
        Dictionary Should Contain Key    ${first}    likes
        Dictionary Should Contain Key    ${first}    dislikes
    END

Comment List Page Size Is Bounded
    ${resp}=    GET On Session    api    /api/comments/
    ${json}=    Set Variable    ${resp.json()}
    ${results}=    Get From Dictionary    ${json}    results
    ${length}=    Get Length    ${results}
    Should Be True    ${length} <= 50

Can Create Comment On Post As Authenticated User
    Login Test User
    ${posts_resp}=    GET On Session    api    /api/posts/
    ${posts_json}=    Set Variable    ${posts_resp.json()}
    ${results}=    Get From Dictionary    ${posts_json}    results
    ${length}=    Get Length    ${results}
    IF    ${length} > 0
        ${post}=    Get From List    ${results}    0
        ${slug}=    Get From Dictionary    ${post}    slug
        ${token}=    Get CSRF Token
        ${headers}=    Create Dictionary    X-CSRFToken=${token}
        ${body}=    Create Dictionary    body=Robot Framework test comment
        ${resp}=    POST On Session    api    /api/posts/${slug}/comments/    json=${body}    headers=${headers}
        Should Be Equal As Integers    ${resp.status_code}    201
    END

Can Vote Like On Comment As Authenticated User
    Login Test User
    ${posts_resp}=    GET On Session    api    /api/posts/
    ${posts_json}=    Set Variable    ${posts_resp.json()}
    ${results}=    Get From Dictionary    ${posts_json}    results
    ${length}=    Get Length    ${results}
    IF    ${length} > 0
        ${post}=    Get From List    ${results}    0
        ${slug}=    Get From Dictionary    ${post}    slug
        ${token}=    Get CSRF Token
        ${headers}=    Create Dictionary    X-CSRFToken=${token}
        ${body}=    Create Dictionary    body=Robot vote target comment
        ${create}=    POST On Session    api    /api/posts/${slug}/comments/    json=${body}    headers=${headers}
        Should Be Equal As Integers    ${create.status_code}    201
        ${created}=    Set Variable    ${create.json()}
        ${cid}=    Get From Dictionary    ${created}    id
        ${vote_headers}=    Create Dictionary    X-CSRFToken=${token}
        ${vote_body}=    Create Dictionary    vote=like
        ${vote_resp}=    POST On Session
        ...    api
        ...    /api/comments/${cid}/vote/
        ...    json=${vote_body}
        ...    headers=${vote_headers}
        Should Be Equal As Integers    ${vote_resp.status_code}    200
        ${vj}=    Set Variable    ${vote_resp.json()}
        Dictionary Should Contain Key    ${vj}    likes
        Dictionary Should Contain Key    ${vj}    dislikes
    END

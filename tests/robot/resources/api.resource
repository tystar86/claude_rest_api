*** Settings ***
Library    RequestsLibrary
Library    Collections
Library    Process
Resource   common.resource

*** Variables ***
${MODERATOR_BOOTSTRAP_CMD}    import os; from django.contrib.auth import get_user_model; User=get_user_model(); username=os.environ['MOD_USERNAME']; email=os.environ['MOD_EMAIL']; password=os.environ['MOD_PASSWORD']; u,_=User.objects.get_or_create(username=username,defaults={'email':email,'role':'moderator'}); u.email=email; u.set_password(password); u.role='moderator'; u.save()

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

Ensure Moderator User
    # First try host-based seeding (works when backend uses host Python env).
    &{seed_env}=    Create Dictionary    MOD_USERNAME=${MOD_USERNAME}    MOD_EMAIL=${MOD_EMAIL}    MOD_PASSWORD=${MOD_PASSWORD}
    ${result}=    Run Process
    ...    uv
    ...    run
    ...    python
    ...    manage.py
    ...    shell
    ...    -c
    ...    ${MODERATOR_BOOTSTRAP_CMD}
    ...    cwd=${CURDIR}/../../..
    ...    env=${seed_env}
    ${status}=    Try Moderator Login
    IF    ${status} != 200
        # Fallback for dockerized local stacks where backend DB is in container.
        ${docker_result}=    Run Process
        ...    docker-compose
        ...    exec
        ...    -T
        ...    -e
        ...    MOD_USERNAME=${MOD_USERNAME}
        ...    -e
        ...    MOD_EMAIL=${MOD_EMAIL}
        ...    -e
        ...    MOD_PASSWORD=${MOD_PASSWORD}
        ...    backend
        ...    python
        ...    manage.py
        ...    shell
        ...    -c
        ...    ${MODERATOR_BOOTSTRAP_CMD}
        ...    cwd=${CURDIR}/../../..
        ${status}=    Try Moderator Login
    END
    Should Be Equal As Integers    ${status}    200

Try Moderator Login
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}
    ${payload}=    Create Dictionary    email=${MOD_EMAIL}    password=${MOD_PASSWORD}
    ${resp}=    POST On Session
    ...    api
    ...    /api/auth/login/
    ...    json=${payload}
    ...    headers=${headers}
    ...    expected_status=any
    RETURN    ${resp.status_code}

Login As Moderator
    ${status}=    Try Moderator Login
    Should Be Equal As Integers    ${status}    200

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

Delete Tag Via API
    [Arguments]    ${slug}
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}
    ${resp}=    DELETE On Session
    ...    api
    ...    /api/tags/${slug}/
    ...    headers=${headers}
    ...    expected_status=any
    # Accept 204 (deleted) or 404 (already gone) — both are fine for cleanup

Cleanup API Test Tags
    Login As Moderator
    @{slugs}=    Create List    robot-tag    robotuppertag    robot-mixed
    ...    unique-tag-dupe    case-check-tag    listed-tag
    FOR    ${slug}    IN    @{slugs}
        Delete Tag Via API    ${slug}
    END

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

Create Published Post Via API
    [Arguments]    ${title}    ${body}
    ${token}=    Get CSRF Token
    ${headers}=    Create Dictionary    X-CSRFToken=${token}
    ${payload}=    Create Dictionary    title=${title}    body=${body}    status=published
    ${resp}=    POST On Session
    ...    api
    ...    /api/posts/
    ...    json=${payload}
    ...    headers=${headers}
    Should Be Equal As Integers    ${resp.status_code}    201
    ${data}=    Set Variable    ${resp.json()}
    RETURN    ${data}

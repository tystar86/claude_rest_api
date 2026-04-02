*** Settings ***
Library    Collections
Library    String

*** Variables ***
${API_BASE_URL}    %{API_BASE_URL=http://localhost:8000}
${UI_BASE_URL}     %{UI_BASE_URL=http://localhost:5173}
${BROWSER}         %{BROWSER=chromium}
${TEST_EMAIL}      %{TEST_EMAIL=robot.user@example.com}
${TEST_USERNAME}   %{TEST_USERNAME=robot_user}
${TEST_PASSWORD}   %{TEST_PASSWORD=robot_pass_123}

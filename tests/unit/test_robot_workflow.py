from pathlib import Path


ROBOT_WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "robot-tests.yml"
ROBOT_API_RESOURCE = (
    Path(__file__).resolve().parents[2] / "tests" / "robot" / "resources" / "api.resource"
)


def test_robot_workflow_seeds_moderator_with_swapped_user_model():
    workflow = ROBOT_WORKFLOW.read_text()

    assert "from django.contrib.auth import get_user_model" in workflow
    assert "User = get_user_model()" in workflow
    assert "from django.contrib.auth.models import User" not in workflow
    assert "Profile.objects.filter(user=u).update(role='moderator')" not in workflow
    assert "u.role = 'moderator'" in workflow


def test_robot_api_resource_preserves_path_when_seeding_moderator():
    resource = ROBOT_API_RESOURCE.read_text()

    assert "env=${seed_env}" in resource
    assert "PATH=%{PATH}" in resource
    assert "MOD_USERNAME=${MOD_USERNAME}" in resource
    assert "MOD_EMAIL=${MOD_EMAIL}" in resource
    assert "MOD_PASSWORD=${MOD_PASSWORD}" in resource
    assert "backend" in resource
    assert "sh" in resource
    assert "-lc" in resource
    assert "export MOD_USERNAME='${MOD_USERNAME}';" in resource
    assert 'python manage.py shell -c "${MODERATOR_BOOTSTRAP_CMD}"' in resource

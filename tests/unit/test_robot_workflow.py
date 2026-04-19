from pathlib import Path


ROBOT_WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "robot-tests.yml"


def test_robot_workflow_seeds_moderator_with_swapped_user_model():
    workflow = ROBOT_WORKFLOW.read_text()

    assert "from django.contrib.auth import get_user_model" in workflow
    assert "User = get_user_model()" in workflow
    assert "from django.contrib.auth.models import User" not in workflow
    assert "Profile.objects.filter(user=u).update(role='moderator')" not in workflow
    assert "u.role = 'moderator'" in workflow

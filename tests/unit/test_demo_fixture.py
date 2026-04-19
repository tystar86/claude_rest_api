import json
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from blog.models import Comment, CommentVote, Post, Tag


FIXTURE_PATH = Path(__file__).resolve().parents[2] / "blog" / "fixtures" / "initial_data.json"


def test_demo_fixture_uses_custom_user_model_records():
    fixture = json.loads(FIXTURE_PATH.read_text())
    models = [item["model"] for item in fixture]
    user_records = [item for item in fixture if item["model"] == "accounts.customuser"]

    assert "auth.user" not in models
    assert "accounts.profile" not in models
    assert len(user_records) == 12
    assert all("role" in record["fields"] for record in user_records)
    assert all("bio" in record["fields"] for record in user_records)


@pytest.mark.django_db(transaction=True)
def test_demo_fixture_loads_with_swapped_user_model():
    call_command("loaddata", str(FIXTURE_PATH), verbosity=0)

    User = get_user_model()

    assert User.objects.count() == 12
    assert Tag.objects.count() == 20
    assert Post.objects.count() == 15
    assert Comment.objects.count() == 30
    assert CommentVote.objects.count() == 20

    alex = User.objects.get(username="alex_chen")
    assert alex.role == "admin"
    assert alex.bio.startswith("Lead developer and site administrator.")

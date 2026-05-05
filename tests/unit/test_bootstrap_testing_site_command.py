import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from blog.models import Post


@pytest.mark.django_db(transaction=True)
def test_bootstrap_empty_db_loads_fixture_and_superuser():
    User = get_user_model()
    call_command("bootstrap_testing_server")

    assert Post.objects.exists()
    assert User.objects.filter(username="alex_chen").exists()
    user = User.objects.get(username="testing")
    assert user.email == "testing@testing.com"
    assert user.check_password("testing")


@pytest.mark.django_db(transaction=True)
def test_bootstrap_with_posts_skips_fixture():
    call_command("bootstrap_testing_server")
    first_posts = Post.objects.count()
    call_command("bootstrap_testing_server")

    assert Post.objects.count() == first_posts
    assert Post.objects.exists()
    User = get_user_model()
    assert User.objects.get(username="testing").check_password("testing")


@pytest.mark.django_db(transaction=True)
def test_bootstrap_force_wipes_fixture_leaves_superuser_only():
    User = get_user_model()
    call_command("bootstrap_testing_server")
    assert Post.objects.exists()

    call_command("bootstrap_testing_server", force=True)

    assert Post.objects.count() == 0
    assert User.objects.count() == 1
    user = User.objects.get(username="testing")
    assert user.email == "testing@testing.com"
    assert user.check_password("testing")


@pytest.mark.django_db(transaction=True)
def test_bootstrap_force_on_empty_db_superuser_only():
    User = get_user_model()
    call_command("bootstrap_testing_server", force=True)

    assert Post.objects.count() == 0
    assert User.objects.count() == 1
    assert User.objects.get(username="testing").check_password("testing")

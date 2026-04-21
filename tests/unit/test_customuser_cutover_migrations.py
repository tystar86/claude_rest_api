import pytest
from django.db import connection
from django.db.migrations.loader import MigrationLoader


@pytest.mark.django_db
def test_blog_initial_follows_accounts_customuser_migration():
    """blog.0001_initial depends on the accounts squash so blog never runs before
    CustomUser exists in migration state."""
    loader = MigrationLoader(connection, replace_migrations=False)
    graph = loader.graph
    target = ("blog", "0001_initial")
    plan = graph.forwards_plan(target)
    squashed = ("accounts", "0001_squashed_0005_customuser_cutover")
    assert squashed in plan
    assert plan.index(squashed) < plan.index(target)

import importlib
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.loader import MigrationLoader


def test_accounts_repair_migration_copies_auth_memberships():
    migration = importlib.import_module("accounts.migrations.0004_repair_customuser_table")
    assert migration.COPYABLE_M2M_FIELDS == ("groups", "user_permissions")


def test_accounts_repair_migration_repoints_profile_and_admin_log():
    migration = importlib.import_module("accounts.migrations.0005_repoint_non_blog_user_fks")
    assert migration.USER_FK_TARGETS == (
        ("accounts_profile", "user_id"),
        ("django_admin_log", "user_id"),
    )


def test_blog_repair_migration_repoints_all_blog_user_foreign_keys():
    migration = importlib.import_module("blog.migrations.0006_repoint_user_foreign_keys")
    assert migration.USER_FK_TARGETS == (
        ("blog_post", "author_id"),
        ("blog_comment", "author_id"),
        ("blog_commentvote", "user_id"),
    )


@pytest.mark.django_db
def test_accounts_repair_migration_updates_existing_user_role_and_bio(monkeypatch):
    migration = importlib.import_module("accounts.migrations.0004_repair_customuser_table")
    User = get_user_model()
    existing_user = User.objects.create_user(
        username="existing",
        email="existing@example.com",
        password="pw",
        role="user",
        bio="old bio",
    )
    schema_editor = SimpleNamespace(connection=SimpleNamespace(alias="default"))

    monkeypatch.setattr(migration, "_ensure_customuser_schema", lambda apps, editor: User)
    monkeypatch.setattr(
        migration,
        "_load_profile_rows",
        lambda editor: {existing_user.id: ("moderator", "fresh bio")},
    )
    monkeypatch.setattr(
        migration,
        "_load_auth_user_rows",
        lambda editor: [
            {
                "id": existing_user.id,
                "password": existing_user.password,
                "last_login": existing_user.last_login,
                "is_superuser": existing_user.is_superuser,
                "username": existing_user.username,
                "first_name": existing_user.first_name,
                "last_name": existing_user.last_name,
                "email": existing_user.email,
                "is_staff": existing_user.is_staff,
                "is_active": existing_user.is_active,
                "date_joined": existing_user.date_joined,
            }
        ],
    )
    monkeypatch.setattr(migration, "_copy_m2m_memberships", lambda *args, **kwargs: None)
    monkeypatch.setattr(migration, "_reset_customuser_sequence", lambda *args, **kwargs: None)

    migration._copy_missing_users(apps=None, schema_editor=schema_editor)

    existing_user.refresh_from_db()
    assert existing_user.role == "moderator"
    assert existing_user.bio == "fresh bio"


@pytest.mark.parametrize(
    ("module_name", "table_name", "column_name"),
    [
        ("accounts.migrations.0005_repoint_non_blog_user_fks", "accounts_profile", "user_id"),
        ("blog.migrations.0006_repoint_user_foreign_keys", "blog_post", "author_id"),
    ],
)
def test_repoint_migrations_lookup_constraints_with_regclass_oid(
    monkeypatch, module_name, table_name, column_name
):
    migration = importlib.import_module(module_name)
    captured = {}

    class FakeCursor:
        def execute(self, query, params):
            captured["query"] = query
            captured["params"] = params

        def fetchone(self):
            return ("constraint_name", 123)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    schema_editor = SimpleNamespace(connection=SimpleNamespace(cursor=lambda: FakeCursor()))

    assert migration._find_fk_constraint(schema_editor, table_name, column_name) == (
        "constraint_name",
        123,
    )
    assert "t.oid = to_regclass(%s)" in captured["query"]
    assert "n.nspname = 'public'" not in captured["query"]
    assert captured["params"] == [table_name, column_name]


@pytest.mark.parametrize(
    "module_name",
    [
        "accounts.migrations.0005_repoint_non_blog_user_fks",
        "blog.migrations.0006_repoint_user_foreign_keys",
    ],
)
def test_repoint_migrations_skip_when_fk_already_points_to_customuser(monkeypatch, module_name):
    migration = importlib.import_module(module_name)
    executed_sql = []
    schema_editor = SimpleNamespace(
        connection=SimpleNamespace(vendor="postgresql"),
        quote_name=lambda name: f'"{name}"',
        execute=executed_sql.append,
    )

    monkeypatch.setattr(migration, "_get_table_oid", lambda editor, table_name: 777)
    monkeypatch.setattr(migration, "_table_exists", lambda editor, table_name: True)
    monkeypatch.setattr(
        migration,
        "_find_fk_constraint",
        lambda editor, table_name, column_name: (f"{table_name}_{column_name}_fk", 777),
    )

    migration._repoint_foreign_keys(apps=None, schema_editor=schema_editor)

    assert executed_sql == []


@pytest.mark.django_db
def test_legacy_accounts_migration_path_builds_customuser_profile_state():
    loader = MigrationLoader(connection, replace_migrations=False)

    state = loader.project_state(nodes=[("accounts", "0005_repoint_non_blog_user_fks")])
    custom_user = state.apps.get_model("accounts", "CustomUser")
    profile = state.apps.get_model("accounts", "Profile")

    assert custom_user is not None
    assert profile._meta.get_field("user").remote_field.model is custom_user


@pytest.mark.django_db
def test_blog_initial_follows_accounts_customuser_migration():
    """blog.0001_initial depends on the accounts squash so blog never runs before
    CustomUser exists in migration state, and django_migrations rows match (squash
    replaces 0004; a bare dependency on 0004 breaks squash-only databases)."""
    loader = MigrationLoader(connection, replace_migrations=False)
    graph = loader.graph
    target = ("blog", "0001_initial")
    plan = graph.forwards_plan(target)
    squashed = ("accounts", "0001_squashed_0005_customuser_cutover")
    if squashed in plan:
        assert plan.index(squashed) < plan.index(target)
    else:
        assert plan.index(("accounts", "0004_repair_customuser_table")) < plan.index(target)

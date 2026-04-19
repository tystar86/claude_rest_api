import importlib


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

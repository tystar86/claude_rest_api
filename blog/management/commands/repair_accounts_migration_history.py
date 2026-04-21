"""
Fix InconsistentMigrationHistory on deploy when blog.0001_initial's graph parent
resolves to accounts.0005_repoint_non_blog_user_fks but that row is missing from
django_migrations (common with squash vs. unsquashed history).

When the accounts squash is only *partially* applied, Django removes the squash
node and repoints blog onto the unsquashed tail (0005). The DB may list 0003 as
applied but not 0004/0005; we must record 0004 before 0005 so check_consistent_history
passes.

Subtle bug this guards against: accounts.0004 wraps CustomUser creation inside a
``SeparateDatabaseAndState`` with ``database_operations=[]`` plus a ``RunPython``
(``_ensure_customuser_schema`` / ``_copy_missing_users``). Faking 0004 skips the
RunPython, so on a database that never had ``accounts_customuser`` (pre-cutover
deploys), marking 0004 applied without running the schema work leaves the table
missing — and the next migration in the chain (blog.0006_repoint_user_foreign_keys)
crashes with ``relation "accounts_customuser" does not exist``. To prevent that,
we detect the missing table and invoke the idempotent RunPython bodies directly
before recording the history rows.

Safe to run every deploy: no-op when the schema matches the history, whether
or not 0005 is already recorded; table-creation path is idempotent
(``_ensure_customuser_schema`` and ``_repoint_foreign_keys`` both check before
mutating). When ``accounts_customuser`` is missing but the 0004 row is already
present (self-recovery from an earlier buggy deploy), we also run the schema
work before short-circuiting on ``has_0005``.

Implementation note: the RunPython bodies are invoked with the *live* Django
app registry rather than historical apps from ``MigrationLoader.project_state``.
Once ``accounts.0004`` and ``0005`` are both recorded as applied, Django's
loader treats the squash's ``replaces`` list as fully applied and collapses
those nodes out of the graph, making ``project_state(("accounts", "0004_..."))``
raise ``NodeNotFoundError``. The live registry works because there are no
post-0004 schema changes to ``CustomUser`` and ``_repoint_foreign_keys`` never
consults ``apps``.

See: django.db.migrations.loader.MigrationLoader.replace_migration (#25945)
"""

from importlib import import_module

from django.apps import apps as global_apps
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

ACCOUNTS_0005 = "0005_repoint_non_blog_user_fks"
ACCOUNTS_0004 = "0004_repair_customuser_table"
ACCOUNTS_0003 = "0003_enforce_sites_dependency"
ACCOUNTS_SQUASH = "0001_squashed_0005_customuser_cutover"
BLOG_0001 = "0001_initial"
CUSTOMUSER_TABLE = "accounts_customuser"


def _customuser_table_exists() -> bool:
    with connection.cursor() as cursor:
        return CUSTOMUSER_TABLE in connection.introspection.table_names(cursor)


def _run_customuser_creation(stdout) -> None:
    """
    Execute the idempotent bodies of accounts.0004 and 0005 against the live
    schema. Creates ``accounts_customuser`` (copying from ``auth_user``/
    ``accounts_profile`` when present) and repoints non-blog user FKs — which
    is exactly what the RunPython operations in those migrations would do if
    run unfaked.

    We pass the *live* Django app registry instead of the historical apps
    returned by ``MigrationLoader.project_state``. Rationale: once a prior
    deploy has recorded both 0004 and 0005 in ``django_migrations``, Django's
    loader considers the squash's ``replaces`` list fully applied and collapses
    the graph, dropping nodes ``accounts.0004`` / ``accounts.0005``. Calling
    ``project_state(("accounts", "0004_..."))`` then raises ``NodeNotFoundError``.
    The live registry is safe to use here because there are no post-0004
    schema changes to ``CustomUser`` (migration 0005 only alters ``profile.user``),
    so the live model matches what 0004 would historically produce; and
    ``_repoint_foreign_keys`` does not consult ``apps`` at all (only raw SQL
    and ``schema_editor``).
    """
    m0004 = import_module("accounts.migrations.0004_repair_customuser_table")
    m0005 = import_module("accounts.migrations.0005_repoint_non_blog_user_fks")

    with connection.schema_editor() as schema_editor:
        stdout.write(
            f"{CUSTOMUSER_TABLE} missing — running accounts.0004 data migration "
            "to create the table and copy users."
        )
        m0004._copy_missing_users(global_apps, schema_editor)
        stdout.write("Running accounts.0005 data migration to repoint non-blog user FKs.")
        m0005._repoint_foreign_keys(global_apps, schema_editor)


class Command(BaseCommand):
    help = "Record accounts.0005 as applied when migration graph expects it but django_migrations lacks the row."

    def handle(self, *args, **options):
        recorder = MigrationRecorder(connection)
        if not recorder.has_table():
            return

        applied = recorder.applied_migrations()
        has_0004 = ("accounts", ACCOUNTS_0004) in applied
        has_0005 = ("accounts", ACCOUNTS_0005) in applied
        has_squash = ("accounts", ACCOUNTS_SQUASH) in applied
        has_0003 = ("accounts", ACCOUNTS_0003) in applied
        blog_0001 = ("blog", BLOG_0001) in applied

        record_0004 = False
        record_0005 = False

        if not has_0005:
            if has_0004 or has_squash:
                record_0005 = True
            elif blog_0001 and has_0003:
                # Partial squash: graph parent is 0005 but 0004 row may also be missing.
                record_0004 = not has_0004
                record_0005 = True

        # Self-heal: whenever the 0004 (or squash) row is present — or about
        # to be recorded — but ``accounts_customuser`` is physically missing,
        # run the idempotent RunPython bodies so the schema matches the
        # history rows. Covers:
        #   (a) fresh partial-squash repairs on pre-cutover databases (the
        #       case the prior revision of this command already handled), and
        #   (b) self-recovery from an earlier buggy deploy that faked 0004
        #       (and 0005) without running their RunPython bodies — the state
        #       where ``has_0005`` is already True but the table never got
        #       created. Without this, we would early-return and migrate
        #       would crash on blog.0006_repoint_user_foreign_keys forever.
        if (record_0004 or has_0004 or has_squash) and not _customuser_table_exists():
            _run_customuser_creation(self.stdout)

        if has_0005:
            return

        if not record_0005:
            self.stdout.write(
                "accounts migration repair skipped "
                f"(blog_0001={blog_0001}, has_0003={has_0003}, "
                f"has_0004={has_0004}, has_squash={has_squash})."
            )
            return

        if record_0004:
            self.stdout.write(
                f"Recording accounts.{ACCOUNTS_0004} as applied (one-time history repair)."
            )
            recorder.record_applied("accounts", ACCOUNTS_0004)

        self.stdout.write(
            f"Recording accounts.{ACCOUNTS_0005} as applied (one-time history repair)."
        )
        recorder.record_applied("accounts", ACCOUNTS_0005)

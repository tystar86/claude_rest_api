"""
Fix InconsistentMigrationHistory on deploy when blog.0001_initial's graph parent
resolves to accounts.0005_repoint_non_blog_user_fks but that row is missing from
django_migrations (common with squash vs. unsquashed history).

When the accounts squash is only *partially* applied, Django removes the squash
node and repoints blog onto the unsquashed tail (0005). The DB may list 0003 as
applied but not 0004/0005; we must record 0004 before 0005 so check_consistent_history
passes.

Safe to run every deploy: no-op if 0005 is already recorded or prerequisites
are absent.

See: django.db.migrations.loader.MigrationLoader.replace_migration (#25945)
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

ACCOUNTS_0005 = "0005_repoint_non_blog_user_fks"
ACCOUNTS_0004 = "0004_repair_customuser_table"
ACCOUNTS_0003 = "0003_enforce_sites_dependency"
ACCOUNTS_SQUASH = "0001_squashed_0005_customuser_cutover"
BLOG_0001 = "0001_initial"


class Command(BaseCommand):
    help = "Record accounts.0005 as applied when migration graph expects it but django_migrations lacks the row."

    def handle(self, *args, **options):
        recorder = MigrationRecorder(connection)
        if not recorder.has_table():
            return

        if recorder.migration_qs.filter(app="accounts", name=ACCOUNTS_0005).exists():
            return

        applied = recorder.applied_migrations()
        has_0004 = ("accounts", ACCOUNTS_0004) in applied
        has_squash = ("accounts", ACCOUNTS_SQUASH) in applied
        has_0003 = ("accounts", ACCOUNTS_0003) in applied
        blog_0001 = ("blog", BLOG_0001) in applied

        record_0004 = False
        record_0005 = False

        if has_0004 or has_squash:
            record_0005 = True
        elif blog_0001 and has_0003:
            # Partial squash: graph parent is 0005 but 0004 row may also be missing.
            record_0004 = not has_0004
            record_0005 = True

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

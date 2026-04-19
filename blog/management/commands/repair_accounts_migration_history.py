"""
Fix InconsistentMigrationHistory on deploy when blog.0001_initial's graph parent
resolves to accounts.0005_repoint_non_blog_user_fks but that row is missing from
django_migrations (common with squash vs. unsquashed history).

Safe to run every deploy: no-op if 0005 is already recorded or prerequisites
are absent.

See: django.db.migrations.graph.MigrationGraph.remove_replacement_node
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

ACCOUNTS_0005 = "0005_repoint_non_blog_user_fks"
ACCOUNTS_0004 = "0004_repair_customuser_table"
ACCOUNTS_SQUASH = "0001_squashed_0005_customuser_cutover"


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
        if not (has_0004 or has_squash):
            return

        self.stdout.write(
            f"Recording accounts.{ACCOUNTS_0005} as applied (one-time history repair)."
        )
        recorder.record_applied("accounts", ACCOUNTS_0005)

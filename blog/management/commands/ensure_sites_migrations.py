"""
Resolves the split state where django.contrib.sites migration records exist
(or don't) but the django_site table is absent, caused by a history where
socialaccount migrations ran before sites migrations.

Strategy: instead of fighting the migration executor (which fails because
socialaccount's applied state references sites.site before sites is set up),
we create the table directly via Django's schema editor, seed the required
default row, and record the two sites migrations as applied.

Handles all three cases automatically:
  1. Clean  — records present AND table exists  → no-op.
  2. Stale  — records present BUT table missing → drops stale records, creates
              table, re-records.
  3. Fresh  — no records AND no table           → creates table, records.

Safe to run on every deployment (idempotent).

Usage:
    python manage.py ensure_sites_migrations
    python manage.py migrate
"""

from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils.timezone import now

SITES_MIGRATIONS = ["0001_initial", "0002_alter_domain_unique"]


def _table_exists():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name   = 'django_site'
            )
            """
        )
        return cursor.fetchone()[0]


def _recorded_migrations():
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM django_migrations WHERE app = %s", ["sites"])
        return {row[0] for row in cursor.fetchall()}


def _remove_stale_records():
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM django_migrations WHERE app = %s", ["sites"])


def _record_migrations():
    with connection.cursor() as cursor:
        for name in SITES_MIGRATIONS:
            cursor.execute(
                "INSERT INTO django_migrations (app, name, applied) "
                "VALUES (%s, %s, %s)",
                ["sites", name, now()],
            )


def _create_table_and_seed():
    """Create django_site using Django's schema editor and seed the default row."""
    with connection.schema_editor() as editor:
        editor.create_model(Site)
    # Seed required default row (allauth and SITE_ID = 1 both rely on this).
    Site.objects.get_or_create(
        id=1, defaults={"domain": "example.com", "name": "example.com"}
    )


class Command(BaseCommand):
    help = (
        "Creates the django_site table and records sites migrations when the "
        "database is in an inconsistent state (socialaccount applied before sites)."
    )

    def handle(self, *args, **options):
        recorded = _recorded_migrations()
        table_exists = _table_exists()

        if recorded and table_exists:
            self.stdout.write("sites already fully applied — nothing to do.")
            return

        if recorded and not table_exists:
            self.stdout.write(
                self.style.WARNING(
                    "Stale migration records found without django_site table. "
                    "Removing stale records…"
                )
            )
            _remove_stale_records()

        self.stdout.write("Creating django_site table…")
        _create_table_and_seed()

        self.stdout.write("Recording sites migrations…")
        _record_migrations()

        self.stdout.write(
            self.style.SUCCESS(
                "django_site table created and sites migrations recorded. "
                "You can now run `migrate` normally."
            )
        )

"""
Resolves split migration state where django_site is missing despite migration
records existing (or vice versa), caused by deployment ordering issues with
django.contrib.sites.

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


def _migrations_table_exists():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name   = 'django_migrations'
            )
            """
        )
        return cursor.fetchone()[0]


def _table_exists(table_name):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name   = %s
            )
            """,
            [table_name],
        )
        return cursor.fetchone()[0]


def _recorded_migrations(app):
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM django_migrations WHERE app = %s", [app])
        return {row[0] for row in cursor.fetchall()}


def _remove_stale_records(app):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM django_migrations WHERE app = %s", [app])


def _record_migrations(app, names):
    with connection.cursor() as cursor:
        for name in names:
            cursor.execute(
                "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                [app, name, now()],
            )


def _fix_sites(stdout, style):
    """Ensure django_site table exists and sites migrations are recorded."""
    if _table_exists("django_site"):
        stdout.write("  django_site — OK")
        return

    recorded = _recorded_migrations("sites")
    if recorded:
        stdout.write(style.WARNING("  django_site — stale records found, removing…"))
        _remove_stale_records("sites")

    stdout.write("  django_site — creating table…")
    with connection.schema_editor() as editor:
        editor.create_model(Site)
    Site.objects.get_or_create(id=1, defaults={"domain": "example.com", "name": "example.com"})
    _record_migrations("sites", SITES_MIGRATIONS)
    stdout.write(style.SUCCESS("  django_site — created and recorded."))


class Command(BaseCommand):
    help = (
        "Ensures django_site exists and sites migrations are recorded correctly "
        "before `migrate` runs."
    )

    def handle(self, *args, **options):
        if not _migrations_table_exists():
            self.stdout.write("Fresh database — nothing to do.")
            return

        _fix_sites(self.stdout, self.style)

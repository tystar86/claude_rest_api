"""
Resolves split migration state where tables are missing despite their
migration records existing (or vice versa), caused by deployment ordering
issues with django.contrib.sites and allauth.socialaccount.

Handles:
  - django_site table (sites app)
  - socialaccount_socialapp_sites M2M table (socialaccount app)

Each is fixed independently using the same strategy:
  0. Brand-new DB — django_migrations doesn't exist yet → no-op.
  1. Clean        — table exists                        → no-op.
  2. Stale        — records present BUT table missing   → drop stale records,
                    create table, re-record.
  3. Ordering bug — no records AND table missing        → create table, record.

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
                "INSERT INTO django_migrations (app, name, applied) "
                "VALUES (%s, %s, %s)",
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
    Site.objects.get_or_create(
        id=1, defaults={"domain": "example.com", "name": "example.com"}
    )
    _record_migrations("sites", SITES_MIGRATIONS)
    stdout.write(style.SUCCESS("  django_site — created and recorded."))


def _fix_socialapp_sites(stdout, style):
    """Ensure socialaccount_socialapp_sites M2M table exists."""
    if _table_exists("socialaccount_socialapp_sites"):
        stdout.write("  socialaccount_socialapp_sites — OK")
        return

    # Import here so this command can run even without allauth installed.
    try:
        from allauth.socialaccount.models import SocialApp
    except ImportError:
        stdout.write(
            "  socialaccount_socialapp_sites — allauth not installed, skipping."
        )
        return

    stdout.write(
        style.WARNING("  socialaccount_socialapp_sites — missing, creating M2M table…")
    )
    through = SocialApp.sites.through
    with connection.schema_editor() as editor:
        editor.create_model(through)
    stdout.write(style.SUCCESS("  socialaccount_socialapp_sites — created."))


class Command(BaseCommand):
    help = (
        "Ensures django_site and socialaccount_socialapp_sites tables exist "
        "and their migrations are recorded correctly before `migrate` runs."
    )

    def handle(self, *args, **options):
        if not _migrations_table_exists():
            self.stdout.write("Fresh database — nothing to do.")
            return

        _fix_sites(self.stdout, self.style)
        _fix_socialapp_sites(self.stdout, self.style)

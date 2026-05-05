"""
Disposable test / VPS bootstrap.

Without arguments: load blog/fixtures/initial_data.json when there are no posts yet,
then ensure the fixed test superuser.

With ``--force``: flush ALL database tables, then recreate only that superuser (no fixtures).

Intended for throwaway databases only.
"""

from __future__ import annotations

from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from blog.models import Post

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "initial_data.json"

TEST_USERNAME = "testing"
TEST_EMAIL = "testing@testing.com"
TEST_PASSWORD = "testing"


class Command(BaseCommand):
    help = (
        "Load demo fixture when the DB has no posts, then ensure superuser "
        f"{TEST_USERNAME!r} / {TEST_EMAIL!r}. "
        "Use --force to flush the database and recreate only that superuser."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Wipe all data (flush) and create only the test superuser.",
        )

    def handle(self, *args, **options):
        User = get_user_model()

        if options["force"]:
            self.stdout.write(self.style.WARNING("Flushing all database tables ..."))
            call_command("flush", interactive=False, verbosity=1)
            self._ensure_test_superuser(User)
            self.stdout.write(
                self.style.SUCCESS(
                    "Database is empty except for the test superuser "
                    f"({TEST_EMAIL!r} / password {TEST_PASSWORD!r})."
                )
            )
            return

        if Post.objects.exists():
            self.stdout.write(
                self.style.WARNING(
                    "Posts already in the database; skipping fixture load. "
                    "Use --force to wipe and start over."
                )
            )
        else:
            if not FIXTURE_PATH.is_file():
                self.stderr.write(f"Fixture missing: {FIXTURE_PATH}")
                raise SystemExit(1)
            self.stdout.write(f"Loading fixture {FIXTURE_PATH.name} ...")
            call_command("loaddata", str(FIXTURE_PATH), verbosity=1)

        self._ensure_test_superuser(User)
        self.stdout.write(
            self.style.SUCCESS(
                f"Superuser {TEST_USERNAME!r} ({TEST_EMAIL!r}) is ready "
                f"(log in with email if your API uses email)."
            )
        )

    def _ensure_test_superuser(self, User):
        with transaction.atomic():
            user, _created = User.objects.update_or_create(
                username=TEST_USERNAME,
                defaults={
                    "email": TEST_EMAIL,
                    "is_staff": True,
                    "is_superuser": True,
                    "is_active": True,
                    "role": User.Role.ADMIN,
                },
            )
            user.set_password(TEST_PASSWORD)
            user.save()

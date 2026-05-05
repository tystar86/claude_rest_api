"""
Disposable test / VPS bootstrap.

Without arguments: load blog/fixtures/initial_data.json when there are no posts yet,
then ensure the configured test superuser.

With ``--force``: flush ALL database tables, then recreate only that superuser (no fixtures).

Superuser username, email, and password come from Django settings (typically
``TESTING_BOOTSTRAP_SUPERUSER_*`` in ``.env.testing``). Defaults match the historic
``testing`` / ``testing@testing.com`` / ``testing`` values.

Intended for throwaway databases only.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from blog.models import Post

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "initial_data.json"


class Command(BaseCommand):
    help = (
        "Load demo fixture when the DB has no posts, then ensure the test superuser "
        "from TESTING_BOOTSTRAP_SUPERUSER_* settings. "
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
        username = settings.TESTING_BOOTSTRAP_SUPERUSER_USERNAME
        email = settings.TESTING_BOOTSTRAP_SUPERUSER_EMAIL
        password = settings.TESTING_BOOTSTRAP_SUPERUSER_PASSWORD

        if options["force"]:
            self.stdout.write(self.style.WARNING("Flushing all database tables ..."))
            call_command("flush", interactive=False, verbosity=1)
            self._ensure_test_superuser(User, username, email, password)
            self.stdout.write(
                self.style.SUCCESS(
                    "Database is empty except for the test superuser "
                    f"({email!r} / password {password!r})."
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
                raise CommandError(f"Fixture missing: {FIXTURE_PATH}")
            self.stdout.write(f"Loading fixture {FIXTURE_PATH.name} ...")
            call_command("loaddata", str(FIXTURE_PATH), verbosity=1)

        self._ensure_test_superuser(User, username, email, password)
        self.stdout.write(
            self.style.SUCCESS(
                f"Superuser {username!r} ({email!r}) is ready "
                "(log in with email if your API uses email)."
            )
        )

    def _ensure_test_superuser(self, User, username: str, email: str, password: str):
        with transaction.atomic():
            user, _created = User.objects.update_or_create(
                username=username,
                defaults={
                    "email": email,
                    "is_staff": True,
                    "is_superuser": True,
                    "is_active": True,
                    "role": User.Role.ADMIN,
                },
            )
            user.set_password(password)
            user.save()

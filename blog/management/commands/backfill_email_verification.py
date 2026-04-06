"""
Management command to backfill allauth EmailAddress records for users that
were created before email verification was enabled.

Usage:
  # Create EmailAddress records only (safe, no emails sent):
  python manage.py backfill_email_verification

  # Also send a verification email to each unverified user:
  python manage.py backfill_email_verification --send-emails

  # Dry-run to see which users would be affected:
  python manage.py backfill_email_verification --dry-run
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.test import RequestFactory

from allauth.account.internal.flows.email_verification import (
    send_verification_email_for_user,
)
from allauth.account.utils import has_verified_email, setup_user_email


class Command(BaseCommand):
    help = "Backfill allauth EmailAddress records for users without one."

    def add_arguments(self, parser):
        parser.add_argument(
            "--send-emails",
            action="store_true",
            default=False,
            help="Send a verification email to each user that gets backfilled.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Print affected users without making any changes.",
        )

    def handle(self, *args, **options):
        send_emails = options["send_emails"]
        dry_run = options["dry_run"]

        # A minimal fake request is needed by allauth's email helpers.
        factory = RequestFactory()
        fake_request = factory.get("/")

        users = User.objects.filter(is_active=True).order_by("pk")
        backfilled = 0
        already_ok = 0
        email_errors = 0

        for user in users:
            if not user.email:
                self.stdout.write(
                    self.style.WARNING(f"  skip user_id={user.pk} (no email address)")
                )
                continue

            if has_verified_email(user):
                already_ok += 1
                continue

            if dry_run:
                self.stdout.write(
                    f"  [dry-run] would backfill user_id={user.pk} ({user.email})"
                )
                backfilled += 1
                continue

            setup_user_email(fake_request, user, [])
            backfilled += 1
            self.stdout.write(f"  backfilled user_id={user.pk} ({user.email})")

            if send_emails:
                try:
                    send_verification_email_for_user(fake_request, user)
                    self.stdout.write(f"    verification email sent to {user.email}")
                except Exception as exc:
                    email_errors += 1
                    self.stderr.write(f"    ERROR sending email to {user.email}: {exc}")

        verb = "would backfill" if dry_run else "backfilled"
        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {verb} {backfilled} user(s); "
                f"{already_ok} already verified; "
                f"{email_errors} email error(s)."
            )
        )

"""Send a portal notification to every active user without a verified email.

The notification links to /verify-email, which opens the email OTP
verification modal for authenticated users. Safe to re-run: each user has a
stable dedupe key, so an existing reminder is refreshed (keeping its read
state) instead of duplicated, and verified users never receive one. The
reminder is deleted automatically when the user completes verification.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from notifications.services import notify_email_verification_reminder


class Command(BaseCommand):
    help = "Notify active users with an unverified email to verify it in the portal."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only report how many users would be notified.',
        )

    def handle(self, *args, **options):
        users = get_user_model().objects.filter(is_active=True, is_email_verified=False)
        count = users.count()

        if options['dry_run']:
            self.stdout.write(f"Would notify {count} user(s) with an unverified email.")
            return

        for user in users.iterator():
            notify_email_verification_reminder(user)
        self.stdout.write(self.style.SUCCESS(f"Sent email verification reminders to {count} user(s)."))

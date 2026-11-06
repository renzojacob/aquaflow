"""
Feature C daily job: remind households two days before their predicted run-out.

    python manage.py send_refill_reminders              # today (Asia/Manila)
    python manage.py send_refill_reminders --dry-run    # list who would be reminded
    python manage.py send_refill_reminders --date 2026-11-10

Run it once every morning, before the ordering cutoff, e.g. cron at 06:30 Manila time:
    30 6 * * *  cd /srv/aquaflow/backend && .venv/bin/python manage.py send_refill_reminders

Safe to run more than once a day: each prediction gets at most one reminder per channel.
A day the job did not run is caught up the next morning, as long as run-out has not passed.
Skips customers with reminders turned off and households with an order already in progress.
Emails are queued in EmailLog (template "refill_reminder") for the email sender to deliver.
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date

from apps.predictions.services import send_due_reminders


class Command(BaseCommand):
    help = "Send refill reminders (in-app + email) to households about to run out of water."

    def add_arguments(self, parser):
        parser.add_argument("--date", help="Pretend today is this date (YYYY-MM-DD).")
        parser.add_argument("--dry-run", action="store_true", help="Only list who is due.")

    def handle(self, *args, date=None, dry_run=False, **opts):
        today = None
        if date:
            today = parse_date(date)
            if today is None:
                raise CommandError("--date must be YYYY-MM-DD")
        results = send_due_reminders(today=today, dry_run=dry_run)
        sent = 0
        for p, channels in results:
            who = p.customer.get_full_name() or p.customer.username
            what = "would remind" if dry_run else (", ".join(channels) or "already reminded")
            self.stdout.write(f"  {who} ({p.address.label}): runs out {p.predicted_runout_date} -> {what}")
            sent += bool(channels)
        verb = "due" if dry_run else "reminded"
        self.stdout.write(self.style.SUCCESS(f"{len(results) if dry_run else sent} household(s) {verb}."))

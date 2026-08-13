from django.core.management.base import BaseCommand
from django.utils import timezone

from borrowings.models import Borrowing
from notifications.tasks import notify_overdue_borrowing


class Command(BaseCommand):
    def handle(self, *args, **options):
        overdue = Borrowing.objects.filter(
            actual_return_date__isnull=True,
            expected_return_date__lt=timezone.localdate(),
        )

        for borrowing in overdue:
            notify_overdue_borrowing(borrowing.id)

        self.stdout.write(
            self.style.SUCCESS(
                f"Checked overdue borrowings: {overdue.count()} found."
            )
        )

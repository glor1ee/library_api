from django.core.management.base import BaseCommand
from django_q.models import Schedule


class Command(BaseCommand):
    def handle(self, *args, **options):
        Schedule.objects.get_or_create(
            name="check_overdue_borrowings",
            defaults={
                "func": "django.core.management.call_command",
                "args": "'check_overdue_borrowings'",
                "schedule_type": Schedule.DAILY,
            },
        )
        self.stdout.write(self.style.SUCCESS("Schedules registered."))

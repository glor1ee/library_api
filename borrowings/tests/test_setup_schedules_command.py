from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django_q.models import Schedule


class SetupSchedulesCommandTests(TestCase):
    def test_registers_daily_schedule(self):
        call_command("setup_schedules", stdout=StringIO())

        self.assertTrue(
            Schedule.objects.filter(name="check_overdue_borrowings").exists()
        )

    def test_idempotent(self):
        call_command("setup_schedules", stdout=StringIO())
        call_command("setup_schedules", stdout=StringIO())

        self.assertEqual(
            Schedule.objects.filter(name="check_overdue_borrowings").count(), 1
        )

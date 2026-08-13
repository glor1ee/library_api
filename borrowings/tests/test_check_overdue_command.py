from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from books.models import Book
from borrowings.models import Borrowing


class CheckOverdueBorrowingsCommandTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="user@example.com", password="testpass123"
        )
        self.book = Book.objects.create(
            title="Sample Book",
            author="Sample Author",
            cover=Book.Cover.SOFT,
            inventory=5,
            daily_fee="1.50",
        )

    @patch(
        "borrowings.management.commands.check_overdue_borrowings"
        ".notify_overdue_borrowing"
    )
    def test_notifies_only_overdue_unreturned_borrowings(self, mock_notify):
        overdue = Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=timezone.localdate() - timedelta(days=1),
        )
        Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=timezone.localdate() + timedelta(days=3),
        )
        Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=timezone.localdate() - timedelta(days=1),
            actual_return_date=timezone.localdate(),
        )

        call_command("check_overdue_borrowings", stdout=StringIO())

        mock_notify.assert_called_once_with(overdue.id)

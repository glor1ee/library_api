from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from books.models import Book
from borrowings.models import Borrowing
from notifications.tasks import notify_borrowing_created, notify_overdue_borrowing


class NotificationTasksTests(TestCase):
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
        self.borrowing = Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=timezone.localdate() + timedelta(days=3),
        )

    @patch("notifications.tasks.send_telegram_message")
    def test_notify_borrowing_created(self, mock_send):
        notify_borrowing_created(self.borrowing.id)

        mock_send.assert_called_once()
        message = mock_send.call_args[0][0]
        self.assertIn(self.book.title, message)
        self.assertIn(self.user.email, message)

    @patch("notifications.tasks.send_telegram_message")
    def test_notify_overdue_borrowing(self, mock_send):
        notify_overdue_borrowing(self.borrowing.id)

        mock_send.assert_called_once()
        message = mock_send.call_args[0][0]
        self.assertIn(self.book.title, message)

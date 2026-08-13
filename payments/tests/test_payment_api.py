from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from books.models import Book
from borrowings.models import Borrowing
from payments.models import Payment

PAYMENT_LIST_URL = reverse("payments:payment-list")
SUCCESS_URL = reverse("payments:success")
CANCEL_URL = reverse("payments:cancel")


def detail_url(payment_id):
    return reverse("payments:payment-detail", args=[payment_id])


class PaymentApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@example.com", password="testpass123"
        )
        self.other_user = get_user_model().objects.create_user(
            email="other@example.com", password="testpass123"
        )
        self.admin = get_user_model().objects.create_user(
            email="admin@example.com", password="testpass123", is_staff=True
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
        self.other_borrowing = Borrowing.objects.create(
            book=self.book,
            user=self.other_user,
            expected_return_date=timezone.localdate() + timedelta(days=3),
        )
        self.payment = Payment.objects.create(
            borrowing=self.borrowing,
            payment_type=Payment.Type.PAYMENT,
            money_to_pay="4.50",
            session_id="sess_test_123",
        )
        self.other_payment = Payment.objects.create(
            borrowing=self.other_borrowing,
            payment_type=Payment.Type.PAYMENT,
            money_to_pay="4.50",
        )

    def test_list_requires_authentication(self):
        res = self.client.get(PAYMENT_LIST_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_sees_only_own_payments(self):
        self.client.force_authenticate(self.user)

        res = self.client.get(PAYMENT_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["id"], self.payment.id)

    def test_admin_sees_all_payments(self):
        self.client.force_authenticate(self.admin)

        res = self.client.get(PAYMENT_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 2)

    def test_retrieve_own_payment_detail(self):
        self.client.force_authenticate(self.user)

        res = self.client.get(detail_url(self.payment.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.payment.id)

    def test_cannot_retrieve_others_payment(self):
        self.client.force_authenticate(self.user)

        res = self.client.get(detail_url(self.other_payment.id))

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    @patch("payments.views.stripe_utils.is_session_paid", return_value=True)
    def test_success_endpoint_marks_payment_paid(self, mock_is_paid):
        self.client.force_authenticate(self.user)

        res = self.client.get(SUCCESS_URL, {"session_id": self.payment.session_id})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PAID)

    @patch("payments.views.stripe_utils.is_session_paid", return_value=False)
    def test_success_endpoint_keeps_pending_when_unpaid(self, mock_is_paid):
        self.client.force_authenticate(self.user)

        res = self.client.get(SUCCESS_URL, {"session_id": self.payment.session_id})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PENDING)

    def test_cancel_endpoint(self):
        self.client.force_authenticate(self.user)

        res = self.client.get(CANCEL_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

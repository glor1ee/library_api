from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from books.models import Book
from borrowings.models import Borrowing
from payments.models import Payment

BORROWING_LIST_URL = reverse("borrowings:borrowing-list")


def sample_book(**params):
    defaults = {
        "title": "Sample Book",
        "author": "Sample Author",
        "cover": Book.Cover.SOFT,
        "inventory": 5,
        "daily_fee": "1.50",
    }
    defaults.update(params)
    return Book.objects.create(**defaults)


def detail_url(borrowing_id):
    return reverse("borrowings:borrowing-detail", args=[borrowing_id])


def return_url(borrowing_id):
    return reverse("borrowings:borrowing-return-borrowing", args=[borrowing_id])


class BorrowingApiTests(APITestCase):
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
        self.book = sample_book(inventory=2)
        self.book.refresh_from_db()

    def test_create_borrowing_requires_authentication(self):
        res = self.client.post(BORROWING_LIST_URL, {})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_borrowing_decrements_inventory(self):
        self.client.force_authenticate(self.user)
        payload = {
            "book": self.book.id,
            "expected_return_date": timezone.localdate() + timedelta(days=3),
        }

        res = self.client.post(BORROWING_LIST_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 1)
        borrowing = Borrowing.objects.get(id=res.data["id"])
        self.assertEqual(borrowing.user, self.user)

    def test_create_borrowing_fails_when_out_of_stock(self):
        self.book.inventory = 0
        self.book.save()
        self.client.force_authenticate(self.user)
        payload = {
            "book": self.book.id,
            "expected_return_date": timezone.localdate() + timedelta(days=3),
        }

        res = self.client.post(BORROWING_LIST_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_borrowing_fails_with_past_return_date(self):
        self.client.force_authenticate(self.user)
        payload = {
            "book": self.book.id,
            "expected_return_date": timezone.localdate() - timedelta(days=1),
        }

        res = self.client.post(BORROWING_LIST_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_shows_only_own_borrowings_for_regular_user(self):
        own = Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=timezone.localdate() + timedelta(days=3),
        )
        Borrowing.objects.create(
            book=self.book,
            user=self.other_user,
            expected_return_date=timezone.localdate() + timedelta(days=3),
        )
        self.client.force_authenticate(self.user)

        res = self.client.get(BORROWING_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["id"], own.id)

    def test_admin_can_filter_by_user_id(self):
        Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=timezone.localdate() + timedelta(days=3),
        )
        Borrowing.objects.create(
            book=self.book,
            user=self.other_user,
            expected_return_date=timezone.localdate() + timedelta(days=3),
        )
        self.client.force_authenticate(self.admin)

        res = self.client.get(BORROWING_LIST_URL, {"user_id": self.user.id})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)

    def test_is_active_filter(self):
        active = Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=timezone.localdate() + timedelta(days=3),
        )
        Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=timezone.localdate() + timedelta(days=3),
            actual_return_date=timezone.localdate(),
        )
        self.client.force_authenticate(self.user)

        res = self.client.get(BORROWING_LIST_URL, {"is_active": "true"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["id"], active.id)

    def test_return_borrowing_increments_inventory(self):
        borrowing = Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=timezone.localdate() + timedelta(days=3),
        )
        self.book.inventory = 1
        self.book.save()
        self.client.force_authenticate(self.user)

        res = self.client.post(return_url(borrowing.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 2)
        borrowing.refresh_from_db()
        self.assertIsNotNone(borrowing.actual_return_date)

    def test_return_borrowing_twice_fails(self):
        borrowing = Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=timezone.localdate() + timedelta(days=3),
            actual_return_date=timezone.localdate(),
        )
        self.client.force_authenticate(self.user)

        res = self.client.post(return_url(borrowing.id))

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_cannot_access_others_borrowing(self):
        borrowing = Borrowing.objects.create(
            book=self.book,
            user=self.other_user,
            expected_return_date=timezone.localdate() + timedelta(days=3),
        )
        self.client.force_authenticate(self.user)

        res = self.client.get(detail_url(borrowing.id))

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_borrowing_creates_pending_payment(self):
        self.client.force_authenticate(self.user)
        payload = {
            "book": self.book.id,
            "expected_return_date": timezone.localdate() + timedelta(days=2),
        }

        res = self.client.post(BORROWING_LIST_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        payment = Payment.objects.get(borrowing_id=res.data["id"])
        self.assertEqual(payment.payment_type, Payment.Type.PAYMENT)
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(payment.money_to_pay, self.book.daily_fee * 2)

    def test_return_overdue_borrowing_creates_fine_payment(self):
        borrowing = Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=timezone.localdate() - timedelta(days=2),
        )
        self.client.force_authenticate(self.user)

        res = self.client.post(return_url(borrowing.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        fine = Payment.objects.get(borrowing=borrowing, payment_type=Payment.Type.FINE)
        self.assertEqual(fine.money_to_pay, self.book.daily_fee * 2 * 2)

    def test_return_on_time_creates_no_fine_payment(self):
        borrowing = Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=timezone.localdate() + timedelta(days=2),
        )
        self.client.force_authenticate(self.user)

        res = self.client.post(return_url(borrowing.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(
            Payment.objects.filter(
                borrowing=borrowing, payment_type=Payment.Type.FINE
            ).exists()
        )

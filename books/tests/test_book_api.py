from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from books.models import Book

BOOK_LIST_URL = reverse("books:book-list")


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


def detail_url(book_id):
    return reverse("books:book-detail", args=[book_id])


class BookApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@example.com", password="testpass123"
        )
        self.admin = get_user_model().objects.create_user(
            email="admin@example.com", password="testpass123", is_staff=True
        )

    def test_list_books_requires_authentication(self):
        res = self.client.get(BOOK_LIST_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_books(self):
        sample_book()
        sample_book(title="Another")
        self.client.force_authenticate(self.user)

        res = self.client.get(BOOK_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 2)

    def test_retrieve_book_detail(self):
        book = sample_book()
        self.client.force_authenticate(self.user)

        res = self.client.get(detail_url(book.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], book.title)

    def test_regular_user_cannot_create_book(self):
        self.client.force_authenticate(self.user)
        payload = {
            "title": "New Book",
            "author": "New Author",
            "cover": Book.Cover.HARD,
            "inventory": 3,
            "daily_fee": "2.00",
        }

        res = self.client.post(BOOK_LIST_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_book(self):
        self.client.force_authenticate(self.admin)
        payload = {
            "title": "New Book",
            "author": "New Author",
            "cover": Book.Cover.HARD,
            "inventory": 3,
            "daily_fee": "2.00",
        }

        res = self.client.post(BOOK_LIST_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Book.objects.count(), 1)

    def test_regular_user_cannot_update_book(self):
        book = sample_book()
        self.client.force_authenticate(self.user)

        res = self.client.patch(detail_url(book.id), {"inventory": 10})

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_book(self):
        book = sample_book()
        self.client.force_authenticate(self.admin)

        res = self.client.patch(detail_url(book.id), {"inventory": 10})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        book.refresh_from_db()
        self.assertEqual(book.inventory, 10)

    def test_admin_can_delete_book(self):
        book = sample_book()
        self.client.force_authenticate(self.admin)

        res = self.client.delete(detail_url(book.id))

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Book.objects.count(), 0)

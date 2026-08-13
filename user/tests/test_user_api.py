from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

REGISTER_URL = reverse("user:register")
TOKEN_URL = reverse("user:token_obtain_pair")
ME_URL = reverse("user:manage")


class UserApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_user(self):
        payload = {
            "email": "user@example.com",
            "password": "testpass123",
            "first_name": "Jane",
            "last_name": "Doe",
        }

        res = self.client.post(REGISTER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload["email"])
        self.assertTrue(user.check_password(payload["password"]))
        self.assertNotIn("password", res.data)

    def test_register_existing_email_fails(self):
        get_user_model().objects.create_user(
            email="user@example.com", password="testpass123"
        )
        payload = {"email": "user@example.com", "password": "testpass123"}

        res = self.client.post(REGISTER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_obtain_token_for_valid_credentials(self):
        get_user_model().objects.create_user(
            email="user@example.com", password="testpass123"
        )
        payload = {"email": "user@example.com", "password": "testpass123"}

        res = self.client.post(TOKEN_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_obtain_token_invalid_credentials(self):
        get_user_model().objects.create_user(
            email="user@example.com", password="testpass123"
        )
        payload = {"email": "user@example.com", "password": "wrong"}

        res = self.client.post(TOKEN_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_authentication(self):
        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_and_update_profile(self):
        user = get_user_model().objects.create_user(
            email="user@example.com", password="testpass123"
        )
        self.client.force_authenticate(user)

        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], user.email)

        res = self.client.patch(ME_URL, {"first_name": "Updated"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Updated")

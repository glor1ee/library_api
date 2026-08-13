from django.test import TestCase, override_settings

from payments import stripe_utils
from payments.models import Payment


class StripeUtilsTests(TestCase):
    @override_settings(STRIPE_SECRET_KEY="")
    def test_create_checkout_session_without_key_returns_empty(self):
        payment = Payment(
            id=1,
            borrowing_id=1,
            payment_type=Payment.Type.PAYMENT,
            money_to_pay="4.50",
        )

        url, session_id = stripe_utils.create_checkout_session(payment)

        self.assertEqual(url, "")
        self.assertEqual(session_id, "")

    @override_settings(STRIPE_SECRET_KEY="")
    def test_is_session_paid_without_key_returns_false(self):
        self.assertFalse(stripe_utils.is_session_paid("sess_123"))

    @override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
    def test_is_session_paid_without_session_id_returns_false(self):
        self.assertFalse(stripe_utils.is_session_paid(""))

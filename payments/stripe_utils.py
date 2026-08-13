import logging

import stripe
from django.conf import settings

logger = logging.getLogger(__name__)


def create_checkout_session(payment):
    if not settings.STRIPE_SECRET_KEY:
        logger.warning(
            "STRIPE_SECRET_KEY is not configured; skipping Stripe session creation."
        )
        return "", ""

    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Borrowing #{payment.borrowing_id} ({payment.payment_type})"
                    },
                    "unit_amount": int(payment.money_to_pay * 100),
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=(
            f"{settings.BASE_URL}/api/payments/success/"
            "?session_id={CHECKOUT_SESSION_ID}"
        ),
        cancel_url=f"{settings.BASE_URL}/api/payments/cancel/",
    )
    return session.url, session.id


def is_session_paid(session_id):
    if not settings.STRIPE_SECRET_KEY or not session_id:
        return False

    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.retrieve(session_id)
    return session.payment_status == "paid"

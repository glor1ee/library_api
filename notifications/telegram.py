import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_telegram_message(text):
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        logger.warning(
            "TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID are not configured; "
            "skipping notification: %s",
            text,
        )
        return

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(
        url, data={"chat_id": settings.TELEGRAM_CHAT_ID, "text": text}, timeout=10
    )

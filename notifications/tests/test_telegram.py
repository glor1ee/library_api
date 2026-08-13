from unittest.mock import patch

from django.test import TestCase, override_settings

from notifications.telegram import send_telegram_message


class TelegramNotificationTests(TestCase):
    @override_settings(TELEGRAM_BOT_TOKEN="", TELEGRAM_CHAT_ID="")
    @patch("notifications.telegram.requests.post")
    def test_no_op_when_not_configured(self, mock_post):
        send_telegram_message("hello")
        mock_post.assert_not_called()

    @override_settings(TELEGRAM_BOT_TOKEN="test-token", TELEGRAM_CHAT_ID="12345")
    @patch("notifications.telegram.requests.post")
    def test_sends_message_when_configured(self, mock_post):
        send_telegram_message("hello")

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("bottest-token/sendMessage", args[0])
        self.assertEqual(kwargs["data"]["chat_id"], "12345")
        self.assertEqual(kwargs["data"]["text"], "hello")

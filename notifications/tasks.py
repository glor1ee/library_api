from notifications.telegram import send_telegram_message


def notify_borrowing_created(borrowing_id):
    from borrowings.models import Borrowing

    borrowing = Borrowing.objects.select_related("book", "user").get(id=borrowing_id)
    send_telegram_message(
        f"New borrowing #{borrowing.id}: \"{borrowing.book.title}\" "
        f"borrowed by {borrowing.user.email}, due {borrowing.expected_return_date}."
    )


def notify_overdue_borrowing(borrowing_id):
    from borrowings.models import Borrowing

    borrowing = Borrowing.objects.select_related("book", "user").get(id=borrowing_id)
    send_telegram_message(
        f"Overdue borrowing #{borrowing.id}: \"{borrowing.book.title}\" "
        f"borrowed by {borrowing.user.email} was due "
        f"{borrowing.expected_return_date} and has not been returned."
    )

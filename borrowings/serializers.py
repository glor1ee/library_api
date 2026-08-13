from django.utils import timezone
from django_q.tasks import async_task
from rest_framework import serializers

from books.serializers import BookSerializer
from borrowings.models import Borrowing
from payments import stripe_utils
from payments.models import Payment


class BorrowingListSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book_title",
            "user_email",
        )


class BorrowingDetailSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user_email",
        )


class BorrowingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ("id", "expected_return_date", "book")

    def validate(self, attrs):
        if attrs["book"].inventory < 1:
            raise serializers.ValidationError({"book": "This book is out of stock."})
        if attrs["expected_return_date"] <= timezone.localdate():
            raise serializers.ValidationError(
                {"expected_return_date": "Must be a date after today."}
            )
        return attrs

    def create(self, validated_data):
        book = validated_data["book"]
        book.inventory -= 1
        book.save()
        borrowing = Borrowing.objects.create(
            user=self.context["request"].user, **validated_data
        )

        days = (borrowing.expected_return_date - borrowing.borrow_date).days
        payment = Payment.objects.create(
            borrowing=borrowing,
            payment_type=Payment.Type.PAYMENT,
            money_to_pay=book.daily_fee * max(days, 1),
        )
        payment.session_url, payment.session_id = stripe_utils.create_checkout_session(
            payment
        )
        payment.save()

        async_task("notifications.tasks.notify_borrowing_created", borrowing.id)

        return borrowing

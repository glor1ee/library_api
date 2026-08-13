from django.conf import settings
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingCreateSerializer,
    BorrowingDetailSerializer,
    BorrowingListSerializer,
)
from payments import stripe_utils
from payments.models import Payment


class BorrowingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    def get_queryset(self):
        user = self.request.user
        queryset = Borrowing.objects.select_related("book", "user")

        if user.is_staff:
            user_id = self.request.query_params.get("user_id")
            if user_id:
                queryset = queryset.filter(user_id=user_id)
        else:
            queryset = queryset.filter(user=user)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() in ("true", "1"):
                queryset = queryset.filter(actual_return_date__isnull=True)
            elif is_active.lower() in ("false", "0"):
                queryset = queryset.filter(actual_return_date__isnull=False)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return BorrowingListSerializer
        if self.action == "create":
            return BorrowingCreateSerializer
        return BorrowingDetailSerializer

    @action(detail=True, methods=["post"], url_path="return")
    def return_borrowing(self, request, pk=None):
        borrowing = self.get_object()

        if borrowing.actual_return_date is not None:
            return Response(
                {"detail": "This borrowing has already been returned."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        borrowing.actual_return_date = timezone.localdate()
        borrowing.save()

        borrowing.book.inventory += 1
        borrowing.book.save()

        if borrowing.actual_return_date > borrowing.expected_return_date:
            overdue_days = (
                borrowing.actual_return_date - borrowing.expected_return_date
            ).days
            fine = Payment.objects.create(
                borrowing=borrowing,
                payment_type=Payment.Type.FINE,
                money_to_pay=(
                    borrowing.book.daily_fee * overdue_days * settings.FINE_MULTIPLIER
                ),
            )
            fine.session_url, fine.session_id = stripe_utils.create_checkout_session(
                fine
            )
            fine.save()

        return Response(BorrowingDetailSerializer(borrowing).data)

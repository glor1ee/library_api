from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from payments import stripe_utils
from payments.models import Payment
from payments.serializers import PaymentDetailSerializer, PaymentListSerializer


class PaymentViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    lookup_value_regex = r"\d+"

    def get_queryset(self):
        queryset = Payment.objects.select_related("borrowing")
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(borrowing__user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return PaymentListSerializer
        return PaymentDetailSerializer


class PaymentSuccessView(APIView):
    def get(self, request):
        session_id = request.query_params.get("session_id", "")
        payment = get_object_or_404(Payment, session_id=session_id)

        if stripe_utils.is_session_paid(session_id):
            payment.status = Payment.Status.PAID
            payment.save()

        return Response(
            {
                "status": payment.status,
                "message": "Payment successful." if payment.status == Payment.Status.PAID
                else "Payment is still pending.",
            }
        )


class PaymentCancelView(APIView):
    def get(self, request):
        return Response(
            {
                "message": (
                    "Payment was not completed. You can pay within 24 hours "
                    "using the same payment session."
                )
            }
        )

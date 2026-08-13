from django.db import models

from borrowings.models import Borrowing


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        PAID = "PAID"

    class Type(models.TextChoices):
        PAYMENT = "PAYMENT"
        FINE = "FINE"

    status = models.CharField(
        max_length=7, choices=Status.choices, default=Status.PENDING
    )
    payment_type = models.CharField(max_length=7, choices=Type.choices)
    borrowing = models.ForeignKey(
        Borrowing, related_name="payments", on_delete=models.CASCADE
    )
    session_url = models.URLField(max_length=511, blank=True)
    session_id = models.CharField(max_length=255, blank=True)
    money_to_pay = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"Payment #{self.pk}: {self.payment_type} ({self.status})"

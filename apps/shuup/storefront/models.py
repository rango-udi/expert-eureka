"""Persist wallet simulation movements separately from immutable seed references."""
from django.conf import settings
from django.db import models


class WalletMovement(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reference = models.CharField(max_length=64, unique=True)
    kind = models.CharField(max_length=16)
    amount_minor = models.BigIntegerField()
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=16, default="posted")
    description = models.CharField(max_length=200)
    method = models.CharField(max_length=64)
    occurred_at = models.DateTimeField()

    class Meta:
        ordering = ("-occurred_at", "-pk")

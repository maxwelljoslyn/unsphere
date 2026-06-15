from django.conf import settings
from django.db import models


class GemTransaction(models.Model):
    """Append-only ledger of gem credits (and, in future, debits).

    The ledger is the single source of truth. Two quantities derive from it:

    * Balance = sum(amount) — what the nav counter shows.
    * A rule's lifetime award total = sum of its *positive* amounts. That's the
      high-water mark crediting compares against, so future spends (negative
      amounts) can never make a rule re-award gems it already granted.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gem_transactions",
    )
    amount = models.IntegerField()
    # The GemRuleDef that credited this (e.g. "cardio_distance"). Blank for
    # future non-rule entries such as manual grants or spends.
    rule_key = models.CharField(max_length=100, blank=True)
    # Coarse grouping for per-category stats and future gem-count achievements
    # (e.g. "cardio", "consistency"). Mirrors the crediting rule's category.
    category = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.user} — {self.amount:+d} ({self.rule_key or 'manual'})"

from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from django.db.models import Sum
from django.template.loader import render_to_string

from .gems import GemRuleDef, registry as global_registry
from .models import GemTransaction

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


def gem_balance(user) -> int:
    """The user's spendable gem total: the sum of every ledger entry."""
    total = GemTransaction.objects.filter(user=user).aggregate(total=Sum("amount"))[
        "total"
    ]
    return total or 0


def lifetime_gems(user) -> int:
    """Total gems ever earned: the sum of positive ledger entries only.

    Unlike the spendable balance, this never decreases when gems are spent, so
    it's the right basis for milestones like the first-gem achievement.
    """
    total = GemTransaction.objects.filter(user=user, amount__gt=0).aggregate(
        total=Sum("amount")
    )["total"]
    return total or 0


def _awarded_by_rule(user) -> Dict[str, int]:
    """Lifetime gems each rule has credited this user (positive amounts only).

    This is the idempotency high-water mark: a rule credits only what it hasn't
    already, and future spends (negative amounts) never lower it — so spending
    gems can't make a rule re-award milestones the user already passed.
    """
    rows = (
        GemTransaction.objects.filter(user=user, amount__gt=0)
        .values("rule_key")
        .annotate(total=Sum("amount"))
    )
    return {r["rule_key"]: r["total"] for r in rows}


def grant_gems(user, reg: Dict[str, GemRuleDef] | None = None) -> int:
    """Credit any gems the user is now entitled to but hasn't yet been awarded.

    Returns the number granted on this call (0 if none). Idempotent: re-running
    without new activity grants nothing. Because each credit carries the rule's
    cumulative shortfall, a workout that crosses several thresholds at once is
    recorded as a single combined credit per rule.
    """
    if reg is None:
        reg = global_registry

    awarded = _awarded_by_rule(user)
    granted = 0
    for key, rule in reg.items():
        delta = rule.entitled(user) - awarded.get(key, 0)
        if delta > 0:
            GemTransaction.objects.create(
                user=user, amount=delta, rule_key=key, category=rule.category
            )
            granted += delta
    return granted


def _is_injectable_html(response) -> bool:
    """Only HTML 200s with a body can carry an out-of-band swap."""
    if getattr(response, "streaming", False):
        return False
    if response.status_code != 200:
        return False
    return response.get("Content-Type", "").startswith("text/html")


class GemMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        if not global_registry or not request.user.is_authenticated:
            return response

        granted = grant_gems(request.user)

        # Nothing earned, or a response that can't carry an out-of-band swap
        # (redirect, full-page nav): the gems are already in the ledger, so the
        # next full-page render shows the updated counter via the context
        # processor. A missed toast loses only the flourish, not the gems —
        # hence no acknowledge/requeue machinery as achievements need.
        is_htmx = request.headers.get("HX-Request") == "true"
        if not granted or not (is_htmx and _is_injectable_html(response)):
            return response

        balance = gem_balance(request.user)
        fragment = render_to_string(
            "gems/_toast_oob.html", {"granted": granted, "gem_balance": balance}
        )
        fragment += render_to_string(
            "gems/_nav_gems_oob.html", {"gem_balance": balance}
        )
        response.content = response.content + fragment.encode("utf-8")
        if response.has_header("Content-Length"):
            response["Content-Length"] = str(len(response.content))

        return response

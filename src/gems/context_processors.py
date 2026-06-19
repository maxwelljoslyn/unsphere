"""Supplies the nav gem pill's eligibility and current balance to full-page renders.

The pill is shown once the user has *ever* earned a gem (lifetime >= 1) and stays
shown forever after, even if they spend their balance down to zero — at which
point the readout simply reads 0. Visibility therefore keys off lifetime_gems,
while the readout shows the spendable gem_balance.

On htmx interactions that grant gems, GemMiddleware updates the readout with an
out-of-band swap instead; this is the source of truth for the initial full-page
value.
"""

from __future__ import annotations

from .middleware import gem_balance, lifetime_gems


def nav_gems(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    if not lifetime_gems(user):
        return {}
    return {"has_unlocked_gems": True, "gem_balance": gem_balance(user)}

"""Supplies the current gem balance to full-page renders for the nav counter.

On htmx interactions that grant gems, GemMiddleware updates the counter with an
out-of-band swap instead; this is the source of truth for the initial full-page
value.
"""

from __future__ import annotations

from .middleware import gem_balance


def nav_gems(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {"gem_balance": gem_balance(user)}

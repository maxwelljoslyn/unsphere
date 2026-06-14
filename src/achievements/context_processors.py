"""Surfaces earned-but-unacknowledged achievements to templates.

The durable source of truth is the DB: an Achievement with acknowledged_at=NULL
has not yet been dismissed by the user. This context processor resolves those to
their AchievementDefs for the queue that base.html renders. It does NOT clear
anything — acknowledgment happens client-side via the acknowledge endpoint when
the user clicks "Nice!", so a render that the user never sees can't lose the
celebration.

It runs only on full-page (non-HTMX) responses. HTMX partials don't extend
base.html, so there's no queue to fill there; the middleware injects an
out-of-band swap on those instead.
"""

from __future__ import annotations

from .middleware import unacknowledged_achievements
from .models import Achievement


def nav_achievements(request):
    """Whether the nav should show the Achievements link.

    Hidden until the user earns their first achievement. On full-page renders
    this is the source of truth; the live (no-reload) reveal on the earning
    interaction is handled by AchievementMiddleware via an out-of-band swap.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {"has_achievements": Achievement.objects.filter(user=user).exists()}


def pending_achievements(request):
    if request.headers.get("HX-Request"):
        return {}
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    defs = unacknowledged_achievements(user)
    if not defs:
        return {}
    return {"pending_achievements": defs}

"""Surfaces newly earned achievements to templates.

The middleware stashes earned keys in request.session["pending_achievements"].
This context processor resolves those keys to their AchievementDefs and clears
the session key so each achievement is celebrated exactly once.

It only consumes the pending list on full-page (non-HTMX) responses. HTMX
partials don't extend base.html, so popping there would silently discard
achievements the user never gets to see; instead we leave them for the next
full page load.
"""

from __future__ import annotations

from .achievements import registry
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
    keys = request.session.pop("pending_achievements", None)
    if not keys:
        return {}
    request.session.modified = True
    defs = [registry[k] for k in keys if k in registry]
    return {"pending_achievements": defs}

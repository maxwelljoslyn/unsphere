from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from django.template.loader import render_to_string

from .achievements import AchievementDef, registry as global_registry
from .models import Achievement

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


def check_achievements(
    user, reg: Dict[str, AchievementDef] | None = None
) -> list[AchievementDef]:
    if reg is None:
        reg = global_registry

    earned_keys = set(
        Achievement.objects.filter(user=user).values_list("achievement_key", flat=True)
    )

    new_ones = []
    for key, adef in reg.items():
        if key not in earned_keys and adef.threshold(user):
            Achievement.objects.create(user=user, achievement_key=key)
            new_ones.append(adef)

    return new_ones


def unacknowledged_achievements(
    user, reg: Dict[str, AchievementDef] | None = None
) -> list[AchievementDef]:
    """Defs for the user's earned-but-not-yet-acknowledged achievements.

    This — not the session — is the delivery queue: every render (re)surfaces
    these until the client confirms the dismissal via the acknowledge endpoint,
    so a dropped celebration is shown again rather than lost. Ordered by earn
    time so the client shows them in the order they were unlocked.
    """
    if reg is None:
        reg = global_registry

    keys = (
        Achievement.objects.filter(user=user, acknowledged_at__isnull=True)
        .order_by("earned_at", "id")
        .values_list("achievement_key", flat=True)
    )
    return [reg[k] for k in keys if k in reg]


def _is_injectable_html(response) -> bool:
    """Only HTML 200s with a body can carry an out-of-band celebration."""
    if getattr(response, "streaming", False):
        return False
    if response.status_code != 200:
        return False
    return response.get("Content-Type", "").startswith("text/html")


class AchievementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        # Nothing to check (and no DB query) when the registry is empty.
        if not global_registry or not request.user.is_authenticated:
            return response

        new_ones = check_achievements(request.user)

        # Only htmx HTML responses can carry an out-of-band swap. Everything else
        # (redirects, the JSON-less full page) leaves the earned rows
        # unacknowledged in the DB; the context processor surfaces them on the
        # next full-page render. No session state to stash.
        is_htmx = request.headers.get("HX-Request") == "true"
        if not (is_htmx and _is_injectable_html(response)):
            return response

        # Deliver everything still unacknowledged, not just what was earned on
        # this request, so a celebration whose acknowledgment never reached the
        # server is retried on the next interaction.
        defs = unacknowledged_achievements(request.user)
        if not defs:
            return response

        fragment = render_to_string(
            "achievements/_celebration_oob.html", {"achievements": defs}
        )
        # First-ever achievement(s): reveal the nav link live. It's the first
        # time iff every achievement the user now has was earned just now.
        if new_ones and (
            Achievement.objects.filter(user=request.user).count() == len(new_ones)
        ):
            fragment += render_to_string("achievements/_nav_achievements_oob.html")
        response.content = response.content + fragment.encode("utf-8")
        if response.has_header("Content-Length"):
            response["Content-Length"] = str(len(response.content))

        return response

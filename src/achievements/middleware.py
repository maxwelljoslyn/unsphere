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
        pending_keys = list(request.session.get("pending_achievements", []))
        pending_keys += [a.key for a in new_ones]
        if not pending_keys:
            return response

        is_htmx = request.headers.get("HX-Request") == "true"
        if is_htmx and _is_injectable_html(response):
            # Show it on this very interaction: append an OOB swap that fills the
            # dialog. The client opens it on htmx:afterSettle (i.e. after this
            # swap lands in the DOM).
            defs = [global_registry[k] for k in pending_keys if k in global_registry]
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
            request.session["pending_achievements"] = []
            request.session.modified = True
        else:
            # Redirects / non-htmx responses can't carry the swap; stash for the
            # next full page render (handled by the context processor).
            request.session["pending_achievements"] = pending_keys
            request.session.modified = True

        return response

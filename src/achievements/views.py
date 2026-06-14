from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .achievements import registry
from .models import Achievement


@login_required
def achievement_list(request):
    """Show every defined achievement.

    Identity (name/description/trophy) is revealed only for achievements the
    current user has earned — everything else is a "?". When *other* users have
    earned an achievement the current user hasn't, their usernames and earn
    times are shown anyway, to stoke a little competition.
    """
    rows = Achievement.objects.select_related("user").order_by("earned_at")
    by_key = {}
    for row in rows:
        by_key.setdefault(row.achievement_key, []).append(row)

    items = []
    for key, adef in registry.items():
        earned = by_key.get(key, [])
        mine = next((r for r in earned if r.user_id == request.user.id), None)
        items.append(
            {
                "adef": adef,
                "earned_by_me": mine is not None,
                "my_earned_at": mine.earned_at if mine else None,
                "others": [r for r in earned if r.user_id != request.user.id],
            }
        )

    return render(request, "achievements/achievement_list.html", {"items": items})


@login_required
@require_POST
def acknowledge(request):
    """Mark the given achievement(s) as acknowledged for the current user.

    The client POSTs the key(s) of celebrations the user has dismissed. Marking
    them acknowledged stops them from being redelivered. Only the caller's own
    unacknowledged rows are touched; unknown or already-acknowledged keys are a
    harmless no-op, so a retry is always safe.
    """
    keys = request.POST.getlist("key")
    if keys:
        Achievement.objects.filter(
            user=request.user,
            achievement_key__in=keys,
            acknowledged_at__isnull=True,
        ).update(acknowledged_at=timezone.now())
    return HttpResponse(status=204)

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render

from .gems import registry
from .middleware import lifetime_gems
from .models import GemTransaction


@login_required
def gem_list(request):
    """Show the current user's gem ledger, newest first.

    Each row names its source by resolving the stored rule_key against the gem
    rule registry (so the human name follows the definition, not a copy frozen
    at credit time); entries with no rule_key are future manual grants/spends.
    The running balance the nav shows is the sum of these amounts, supplied for
    the page header by the nav_gems context processor.

    Reachable only by users who have ever earned a gem — the same eligibility
    the nav uses to show the gem pill (lifetime gems >= 1). A user who has spent
    their balance down to zero keeps access, matching the nav. Logged-out users
    are already bounced to login by @login_required; a logged-in user who has
    never earned a gem gets a 404 rather than an empty ledger with no path to it.
    """
    if not lifetime_gems(request.user):
        raise Http404
    txns = GemTransaction.objects.filter(user=request.user)
    rows = []
    for t in txns:
        rule = registry.get(t.rule_key)
        rows.append(
            {
                "signed": f"{t.amount:+d}",
                "source": rule.name if rule else (t.rule_key or "Manual"),
                "category": t.category,
                "created_at": t.created_at,
            }
        )
    return render(request, "gems/gem_list.html", {"txns": rows})

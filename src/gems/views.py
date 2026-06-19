from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .gems import registry
from .models import GemTransaction


@login_required
def gem_list(request):
    """Show the current user's gem ledger, newest first.

    Each row names its source by resolving the stored rule_key against the gem
    rule registry (so the human name follows the definition, not a copy frozen
    at credit time); entries with no rule_key are future manual grants/spends.
    The running balance the nav shows is the sum of these amounts, supplied for
    the page header by the nav_gems context processor.
    """
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

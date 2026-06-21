from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from workouts import analytics


@login_required
def stats(request):
    """Personal stats dashboard: headline tiles plus a few charts.

    All the number-crunching lives in ``workouts.analytics`` so it stays
    reusable; this view only assembles those results and hands the series to the
    template, which emits them as JSON for the client-side charts module to draw.
    """
    user = request.user
    context = {
        "total_workouts": analytics.total_confirmed_workouts(user),
        "current_streak": analytics.current_streak(user),
        "cardio_series": analytics.cardio_cumulative_series(user),
        "day_counts": analytics.workout_day_counts(user),
    }
    return render(request, "stats/stats.html", context)

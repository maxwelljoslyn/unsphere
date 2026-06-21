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
    # Computed once and reused: the headline cardio tiles read their totals off
    # the tail of this same series the line charts plot, so no extra queries.
    cardio_series = analytics.cardio_cumulative_series(user)
    cardio_totals = analytics.cardio_lifetime_totals(cardio_series)
    context = {
        "total_workouts": analytics.total_confirmed_workouts(user),
        "total_exercises": analytics.total_exercises_logged(user),
        "current_streak": analytics.current_streak(user),
        "workout_day_percentage": analytics.workout_day_percentage(user),
        "cardio_miles": cardio_totals["miles"],
        "cardio_hours": cardio_totals["hours"],
        "cardio_series": cardio_series,
        "day_counts": analytics.workout_day_counts(user),
    }
    return render(request, "stats/stats.html", context)

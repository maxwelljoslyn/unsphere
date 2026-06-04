import datetime as dt

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from achievements.models import Achievement

User = get_user_model()


@pytest.mark.django_db
def test_earned_time_emitted_as_utc_iso_for_client_localization(client):
    """Times are rendered server-side as UTC ISO 8601 inside <time data-localize>;
    the browser rewrites them to local time. We assert the markup the JS needs."""
    user = User.objects.create_user(username="alice", password="pw")
    client.force_login(user)
    a = Achievement.objects.create(user=user, achievement_key="one_workout")
    # Pin earned_at to a known UTC instant.
    Achievement.objects.filter(pk=a.pk).update(
        earned_at=dt.datetime(2026, 6, 3, 23, 30, tzinfo=dt.timezone.utc)
    )

    content = client.get(reverse("achievement-list")).content.decode()
    # Machine-readable UTC timestamp for the browser to localize.
    assert 'datetime="2026-06-03T23:30:00+00:00"' in content
    # Marked for client-side localization.
    assert "data-localize" in content
    # Human-readable UTC fallback for the pre-JS / no-JS instant.
    assert "Jun 3, 2026, 23:30 UTC" in content

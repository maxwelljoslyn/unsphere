import datetime as dt

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from workouts.models import Movement, Workout

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="al", password="pw")


@pytest.fixture
def auth_client(client, user):
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_htmx_earn_injects_oob_celebration_and_trigger(auth_client, user):
    movement = Movement.objects.create(name="rower", kind=Movement.CARDIO)
    workout = Workout.objects.create(
        user=user,
        date=dt.datetime(2026, 1, 1, 8, 0, tzinfo=dt.timezone.utc),
        timezone="UTC",
    )
    resp = auth_client.post(
        reverse("cardio-exercise-add", args=[workout.pk]),
        {
            "movement": movement.pk,
            "distance_0": "2",
            "distance_1": "miles",
            "duration_0": "",
            "duration_1": "",
            "notes": "",
        },
        HTTP_HX_REQUEST="true",
    )
    assert resp.status_code == 200
    body = resp.content.decode()
    # Out-of-band swap that refills the client-drained queue. Each earned
    # achievement rides along as its own <template> card so the client can show
    # them one dialog at a time.
    assert 'id="achievement-queue"' in body
    assert 'hx-swap-oob="innerHTML"' in body
    # One <template> card per earned achievement, each its own dialog body (one
    # trophy apiece) — so the client can show them one at a time.
    n_cards = body.count("<template")
    assert n_cards >= 2
    assert body.count("🏆") == n_cards
    assert "Getting Started" in body  # one_workout
    assert "On the Move" in body  # first_cardio
    # Consumed so it won't replay.
    assert auth_client.session.get("pending_achievements", []) == []


@pytest.mark.django_db
def test_non_htmx_redirect_defers_then_full_page_shows(auth_client):
    # A full-page create redirects; the achievement can't ride a 302, so it's
    # stashed for the next render.
    resp = auth_client.post(
        reverse("workout-create"),
        {"date": "2026-02-02T18:30", "timezone": "UTC", "notes": ""},
    )
    assert resp.status_code == 302
    assert "one_workout" in auth_client.session.get("pending_achievements", [])

    # The redirected-to page renders the populated dialog and clears the queue.
    body = auth_client.get(resp.url).content.decode()
    assert "🏆" in body
    assert "Getting Started" in body
    assert auth_client.session.get("pending_achievements", []) == []


@pytest.mark.django_db
def test_empty_dialog_has_no_trophy(auth_client):
    # A page with nothing pending must not contain the trophy (matters for the
    # "locked achievement" rendering on the achievements list).
    body = auth_client.get(reverse("movement-list")).content.decode()
    assert 'id="achievement-dialog"' in body  # shell present for htmx target
    assert "🏆" not in body  # but empty

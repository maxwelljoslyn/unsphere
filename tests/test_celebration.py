import datetime as dt

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from achievements.models import Achievement
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
    # Confirmed up front: per decision A, adding an exercise to an already-saved
    # workout counts live, so this add earns the workout + cardio achievements.
    workout = Workout.objects.create(
        user=user,
        date=dt.datetime(2026, 1, 1, 8, 0, tzinfo=dt.timezone.utc),
        timezone="UTC",
        confirmed_at=dt.datetime(2026, 1, 1, 9, 0, tzinfo=dt.timezone.utc),
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
    # Nothing is consumed server-side: the earned rows stay unacknowledged in the
    # DB and are redelivered until the client confirms dismissal via the ack
    # endpoint, so a delivery the user never sees can't lose the celebration.
    assert (
        Achievement.objects.filter(user=user, acknowledged_at__isnull=True).count()
        == n_cards
    )


@pytest.mark.django_db
def test_non_htmx_redirect_defers_then_full_page_shows(auth_client, user):
    # Creating a workout makes a draft, which counts toward nothing yet.
    workout = Workout.objects.create(
        user=user,
        date=dt.datetime(2026, 2, 2, 18, 30, tzinfo=dt.timezone.utc),
        timezone="UTC",
    )
    assert not Achievement.objects.filter(
        user=user, achievement_key="one_workout"
    ).exists()

    # Confirming is a full-page POST that redirects; the achievement can't ride a
    # 302, so the earned row simply waits, unacknowledged, in the DB.
    resp = auth_client.post(reverse("workout-confirm", args=[workout.pk]))
    assert resp.status_code == 302
    assert Achievement.objects.filter(
        user=user, achievement_key="one_workout", acknowledged_at__isnull=True
    ).exists()

    # The redirected-to page renders the populated dialog from that DB row.
    body = auth_client.get(resp.url).content.decode()
    assert "🏆" in body
    assert "Getting Started" in body
    # Still unacknowledged after rendering: acknowledgment is client-side via the
    # ack endpoint, so a render the user might never see can't lose it.
    assert Achievement.objects.filter(
        user=user, achievement_key="one_workout", acknowledged_at__isnull=True
    ).exists()


@pytest.mark.django_db
def test_empty_dialog_has_no_trophy(auth_client):
    # A page with nothing pending must not contain the trophy (matters for the
    # "locked achievement" rendering on the achievements list).
    body = auth_client.get(reverse("movement-list")).content.decode()
    assert 'id="achievement-dialog"' in body  # shell present for htmx target
    assert "🏆" not in body  # but empty


@pytest.mark.django_db
def test_unacknowledged_redelivered_on_every_full_page_until_acked(auth_client, user):
    # An earned-but-unacknowledged row is surfaced on every full-page render, so
    # a celebration whose dismissal never reached the server isn't lost.
    Achievement.objects.create(user=user, achievement_key="one_workout")

    for _ in range(2):
        body = auth_client.get(reverse("movement-list")).content.decode()
        assert "Getting Started" in body  # redelivered each time

    # Once acknowledged, it stops appearing.
    Achievement.objects.filter(user=user).update(
        acknowledged_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    )
    body = auth_client.get(reverse("movement-list")).content.decode()
    assert "Getting Started" not in body


@pytest.mark.django_db
def test_acknowledge_endpoint_marks_row_and_stops_redelivery(auth_client, user):
    Achievement.objects.create(user=user, achievement_key="one_workout")

    resp = auth_client.post(reverse("achievement-ack"), {"key": "one_workout"})
    assert resp.status_code == 204

    row = Achievement.objects.get(user=user, achievement_key="one_workout")
    assert row.acknowledged_at is not None

    body = auth_client.get(reverse("movement-list")).content.decode()
    assert "Getting Started" not in body  # no longer redelivered


@pytest.mark.django_db
def test_acknowledge_is_idempotent_and_keeps_first_timestamp(auth_client, user):
    # A retried ack (the client re-fires until the server confirms) must not move
    # the recorded acknowledgment time.
    Achievement.objects.create(user=user, achievement_key="one_workout")

    auth_client.post(reverse("achievement-ack"), {"key": "one_workout"})
    first = Achievement.objects.get(
        user=user, achievement_key="one_workout"
    ).acknowledged_at

    resp = auth_client.post(reverse("achievement-ack"), {"key": "one_workout"})
    assert resp.status_code == 204
    assert (
        Achievement.objects.get(
            user=user, achievement_key="one_workout"
        ).acknowledged_at
        == first
    )


@pytest.mark.django_db
def test_acknowledge_only_touches_callers_own_rows(auth_client, user):
    bob = User.objects.create_user(username="bob", password="pw")
    Achievement.objects.create(user=bob, achievement_key="one_workout")

    resp = auth_client.post(reverse("achievement-ack"), {"key": "one_workout"})
    assert resp.status_code == 204

    # Bob's row is untouched even though the key matches.
    assert Achievement.objects.get(user=bob).acknowledged_at is None


@pytest.mark.django_db
def test_acknowledge_requires_login(client):
    resp = client.post(reverse("achievement-ack"), {"key": "one_workout"})
    assert resp.status_code == 302
    assert "/accounts/login/" in resp.url


@pytest.mark.django_db
def test_acknowledge_rejects_get(auth_client):
    resp = auth_client.get(reverse("achievement-ack"))
    assert resp.status_code == 405

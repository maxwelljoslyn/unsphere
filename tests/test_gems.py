import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from django.db.models import Sum

from gems.gems import GemRuleDef
from gems.middleware import gem_balance, grant_gems
from gems.models import GemTransaction
from unsphere.units import u


def _rule_total(user, rule_key):
    return (
        GemTransaction.objects.filter(user=user, rule_key=rule_key).aggregate(
            t=Sum("amount")
        )["t"]
        or 0
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registration(gem_registry):
    rule = GemRuleDef(
        key="r1",
        name="R1",
        category="cardio",
        entitled=lambda user: 0,
        registry=gem_registry,
    )
    assert gem_registry["r1"] is rule


def test_duplicate_key_raises(gem_registry):
    GemRuleDef(
        key="dup",
        name="First",
        category="cardio",
        entitled=lambda user: 0,
        registry=gem_registry,
    )
    with pytest.raises(ValueError, match="dup"):
        GemRuleDef(
            key="dup",
            name="Second",
            category="cardio",
            entitled=lambda user: 0,
            registry=gem_registry,
        )


def test_entitled_not_called_at_construction(gem_registry):
    called = []
    GemRuleDef(
        key="no_call",
        name="No Call",
        category="cardio",
        entitled=lambda user: called.append(True) or 0,
        registry=gem_registry,
    )
    assert called == []


# ---------------------------------------------------------------------------
# Granting / ledger
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_grant_creates_ledger_row(gem_registry, django_user_model):
    user = django_user_model.objects.create_user(username="g1", password="x")
    GemRuleDef(
        key="five",
        name="Five",
        category="cardio",
        entitled=lambda user: 5,
        registry=gem_registry,
    )

    granted = grant_gems(user, reg=gem_registry)

    assert granted == 5
    row = GemTransaction.objects.get(user=user, rule_key="five")
    assert row.amount == 5
    assert row.category == "cardio"


@pytest.mark.django_db
def test_grant_is_idempotent(gem_registry, django_user_model):
    user = django_user_model.objects.create_user(username="g2", password="x")
    GemRuleDef(
        key="flat",
        name="Flat",
        category="cardio",
        entitled=lambda user: 3,
        registry=gem_registry,
    )

    assert grant_gems(user, reg=gem_registry) == 3
    assert grant_gems(user, reg=gem_registry) == 0
    assert GemTransaction.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_grant_credits_only_the_increase(gem_registry, django_user_model):
    user = django_user_model.objects.create_user(username="g3", password="x")
    entitled = {"n": 2}
    GemRuleDef(
        key="grow",
        name="Grow",
        category="cardio",
        entitled=lambda user: entitled["n"],
        registry=gem_registry,
    )

    assert grant_gems(user, reg=gem_registry) == 2
    entitled["n"] = 5
    assert grant_gems(user, reg=gem_registry) == 3
    assert gem_balance(user) == 5


@pytest.mark.django_db
def test_spend_does_not_lower_the_high_water_mark(gem_registry, django_user_model):
    user = django_user_model.objects.create_user(username="g4", password="x")
    GemRuleDef(
        key="hw",
        name="HW",
        category="cardio",
        entitled=lambda user: 4,
        registry=gem_registry,
    )

    assert grant_gems(user, reg=gem_registry) == 4
    # A future sink spends 3 gems: a negative ledger entry, no rule_key.
    GemTransaction.objects.create(user=user, amount=-3)
    assert gem_balance(user) == 1

    # The rule already awarded its 4; the spend must not make it re-award.
    assert grant_gems(user, reg=gem_registry) == 0
    assert gem_balance(user) == 1


# ---------------------------------------------------------------------------
# Ledger page (gem-list view)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_gem_list_requires_login(client):
    from django.urls import reverse

    resp = client.get(reverse("gem-list"))
    assert resp.status_code == 302
    assert "/accounts/login/" in resp.url


@pytest.mark.django_db
def test_gem_list_no_gems_is_not_found(client, django_user_model):
    from django.urls import reverse

    user = django_user_model.objects.create_user(username="broke", password="x")
    client.force_login(user)
    # A user who has never earned a gem hasn't unlocked the pill in the nav, so
    # the page must 404 to match, rather than show an empty ledger they have no
    # link to.
    assert client.get(reverse("gem-list")).status_code == 404


@pytest.mark.django_db
def test_gem_list_shown_when_user_has_gems(client, django_user_model):
    from django.urls import reverse

    user = django_user_model.objects.create_user(username="rich", password="x")
    GemTransaction.objects.create(
        user=user, amount=3, rule_key="seed", category="cardio"
    )
    client.force_login(user)
    assert client.get(reverse("gem-list")).status_code == 200


@pytest.mark.django_db
def test_gem_list_still_shown_when_balance_fully_spent(client, django_user_model):
    from django.urls import reverse

    user = django_user_model.objects.create_user(username="spent", password="x")
    GemTransaction.objects.create(
        user=user, amount=3, rule_key="seed", category="cardio"
    )
    GemTransaction.objects.create(user=user, amount=-3)
    client.force_login(user)
    # Balance is zero but the user has earned gems before, so the page stays
    # reachable — eligibility tracks lifetime earnings, not the spendable
    # balance (the nav pill likewise stays visible, reading 0).
    assert client.get(reverse("gem-list")).status_code == 200


# ---------------------------------------------------------------------------
# Seed rules (against the real global registry)
# ---------------------------------------------------------------------------


@pytest.fixture
def cardio_movement(db):
    from workouts.models import Movement

    return Movement.objects.create(name="cycling", kind=Movement.CARDIO)


def _workout(user, when, tz="UTC", confirmed=True):
    from workouts.models import Workout

    # Confirmed by default: only confirmed workouts count toward gems, so the
    # seed-rule tests below confirm theirs to exercise the counting paths.
    return Workout.objects.create(
        user=user,
        date=when,
        timezone=tz,
        confirmed_at=(when if confirmed else None),
    )


@pytest.mark.django_db
def test_seed_cardio_distance_one_gem_per_mile(django_user_model, cardio_movement):
    from workouts.models import CardioExercise

    user = django_user_model.objects.create_user(username="s1", password="x")
    w = _workout(user, dt.datetime(2026, 6, 14, 12, 0, tzinfo=ZoneInfo("UTC")))
    CardioExercise.objects.create(
        workout=w, movement=cardio_movement, distance=u("3.4 mile")
    )

    grant_gems(user)

    assert _rule_total(user, "cardio_distance") == 3  # floor(3.4)


@pytest.mark.django_db
def test_seed_cardio_distance_sums_and_converts_units(
    django_user_model, cardio_movement
):
    from workouts.models import CardioExercise

    user = django_user_model.objects.create_user(username="s2", password="x")
    w = _workout(user, dt.datetime(2026, 6, 14, 12, 0, tzinfo=ZoneInfo("UTC")))
    CardioExercise.objects.create(
        workout=w, movement=cardio_movement, distance=u("1 mile")
    )
    # ~1.6 km ≈ 1 mile, so the cumulative total clears the 2-mile threshold.
    CardioExercise.objects.create(
        workout=w, movement=cardio_movement, distance=u("1700 meter")
    )

    grant_gems(user)

    assert _rule_total(user, "cardio_distance") == 2


@pytest.mark.django_db
def test_seed_cardio_duration_one_gem_per_ten_minutes(
    django_user_model, cardio_movement
):
    from workouts.models import CardioExercise

    user = django_user_model.objects.create_user(username="s3", password="x")
    w = _workout(user, dt.datetime(2026, 6, 14, 12, 0, tzinfo=ZoneInfo("UTC")))
    CardioExercise.objects.create(
        workout=w, movement=cardio_movement, duration=u("35 min")
    )

    grant_gems(user)

    assert _rule_total(user, "cardio_duration") == 3  # 35 // 10


@pytest.mark.django_db
def test_seed_active_days_counts_distinct_local_days(django_user_model):
    user = django_user_model.objects.create_user(username="s4", password="x")
    # Two workouts on the same local (UTC) day → one active day.
    _workout(user, dt.datetime(2026, 6, 14, 8, 0, tzinfo=ZoneInfo("UTC")))
    _workout(user, dt.datetime(2026, 6, 14, 20, 0, tzinfo=ZoneInfo("UTC")))
    # A different local day → a second.
    _workout(user, dt.datetime(2026, 6, 15, 9, 0, tzinfo=ZoneInfo("UTC")))

    grant_gems(user)

    assert _rule_total(user, "active_days") == 2


@pytest.mark.django_db
def test_draft_workout_does_not_count_until_confirmed(
    django_user_model, cardio_movement
):
    from workouts.models import CardioExercise

    user = django_user_model.objects.create_user(username="s6", password="x")
    w = _workout(
        user,
        dt.datetime(2026, 6, 14, 12, 0, tzinfo=ZoneInfo("UTC")),
        confirmed=False,
    )
    CardioExercise.objects.create(
        workout=w, movement=cardio_movement, distance=u("5 mile")
    )

    grant_gems(user)
    assert gem_balance(user) == 0  # draft: nothing counts yet

    w.confirmed_at = w.date
    w.save(update_fields=["confirmed_at"])
    grant_gems(user)
    assert _rule_total(user, "cardio_distance") == 5
    assert _rule_total(user, "active_days") == 1


@pytest.mark.django_db
def test_seed_active_days_uses_the_workouts_timezone(django_user_model):
    user = django_user_model.objects.create_user(username="s5", password="x")
    # 02:00 UTC is still the previous calendar day in Los Angeles (UTC-7/8),
    # so this counts as a distinct local day from a midday-UTC workout.
    _workout(
        user,
        dt.datetime(2026, 6, 14, 2, 0, tzinfo=ZoneInfo("UTC")),
        tz="America/Los_Angeles",
    )
    _workout(
        user,
        dt.datetime(2026, 6, 14, 18, 0, tzinfo=ZoneInfo("UTC")),
        tz="America/Los_Angeles",
    )

    grant_gems(user)

    assert _rule_total(user, "active_days") == 2

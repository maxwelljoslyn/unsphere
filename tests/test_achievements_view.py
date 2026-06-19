import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from achievements.models import Achievement

User = get_user_model()

# "Getting Started" is the name of the one_workout achievement (see
# achievements/definitions.py); it must stay hidden until the viewer earns it.
KEY = "one_workout"
NAME = "Getting Started"

# A second achievement used as the "not earned by the viewer" case, so its
# identity must stay hidden even when someone else has earned it. The viewer
# earns UNLOCK_KEY (below) only to gain access to the page in the first place.
OTHER_KEY = "three_workouts"
OTHER_NAME = "Warming Up"

# Earning this is what unlocks the page for the viewer in tests that exercise
# the on-page no-spoiler behavior; its identity is expected to be visible.
UNLOCK_KEY = KEY
UNLOCK_NAME = NAME


@pytest.fixture
def alice(db):
    return User.objects.create_user(username="alice", password="pw")


@pytest.fixture
def client_alice(client, alice):
    client.force_login(alice)
    return client


@pytest.mark.django_db
def test_requires_login(client):
    resp = client.get(reverse("achievement-list"))
    assert resp.status_code == 302
    assert "/accounts/login/" in resp.url


@pytest.mark.django_db
def test_no_achievements_is_not_found(client_alice):
    # The page is hidden from the nav until the user earns their first
    # achievement; visiting the URL directly while ineligible must 404, not
    # reveal the (placeholder-filled) page.
    assert client_alice.get(reverse("achievement-list")).status_code == 404


@pytest.mark.django_db
def test_unearned_achievement_shows_only_question_mark(client_alice, alice):
    # alice has unlocked the page by earning one achievement; a *different* one
    # she hasn't earned stays hidden behind a "?".
    Achievement.objects.create(user=alice, achievement_key=UNLOCK_KEY)

    content = client_alice.get(reverse("achievement-list")).content.decode()
    assert "?" in content
    assert OTHER_NAME not in content  # identity of the unearned one hidden


@pytest.mark.django_db
def test_earned_by_other_user_only(client_alice, alice):
    # alice has unlocked the page; bob has earned an achievement alice hasn't.
    Achievement.objects.create(user=alice, achievement_key=UNLOCK_KEY)
    bob = User.objects.create_user(username="bob", password="pw")
    Achievement.objects.create(user=bob, achievement_key=OTHER_KEY)

    content = client_alice.get(reverse("achievement-list")).content.decode()
    assert "bob" in content  # competitor revealed
    assert OTHER_NAME not in content  # but not what they earned
    assert "?" in content


@pytest.mark.django_db
def test_earned_by_current_user(client_alice, alice):
    Achievement.objects.create(user=alice, achievement_key=KEY)

    content = client_alice.get(reverse("achievement-list")).content.decode()
    assert "🏆" in content
    assert NAME in content  # name revealed
    assert content != ""  # description revealed
    assert "You earned this on" in content


@pytest.mark.django_db
def test_earned_by_current_user_also_lists_others(client_alice, alice):
    bob = User.objects.create_user(username="bob", password="pw")
    Achievement.objects.create(user=alice, achievement_key=KEY)
    Achievement.objects.create(user=bob, achievement_key=KEY)

    content = client_alice.get(reverse("achievement-list")).content.decode()
    assert "🏆" in content
    assert NAME in content
    assert "Also earned by:" in content
    assert "bob" in content

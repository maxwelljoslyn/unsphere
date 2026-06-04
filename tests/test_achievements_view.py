import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from achievements.models import Achievement

User = get_user_model()

# "Getting Started" is the name of the one_workout achievement (see
# achievements/definitions.py); it must stay hidden until the viewer earns it.
KEY = "one_workout"
NAME = "Getting Started"


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
def test_unearned_by_anyone_shows_only_question_mark(client_alice):
    content = client_alice.get(reverse("achievement-list")).content.decode()
    assert "?" in content
    assert NAME not in content  # identity hidden
    assert "🏆" not in content  # no trophy for anything


@pytest.mark.django_db
def test_earned_by_other_user_only(client_alice):
    bob = User.objects.create_user(username="bob", password="pw")
    Achievement.objects.create(user=bob, achievement_key=KEY)

    content = client_alice.get(reverse("achievement-list")).content.decode()
    assert "bob" in content  # competitor revealed
    assert NAME not in content  # but not what they earned
    assert "🏆" not in content  # alice hasn't earned it
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

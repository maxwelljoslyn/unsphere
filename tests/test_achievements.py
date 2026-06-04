import pytest
from achievements.achievements import AchievementDef
from achievements.middleware import check_achievements
from achievements.models import Achievement


def test_registration(achievement_registry):
    adef = AchievementDef(
        key="test_one",
        name="Test One",
        description="Testing registration",
        threshold=lambda user: True,
        registry=achievement_registry,
    )
    assert "test_one" in achievement_registry
    assert achievement_registry["test_one"] is adef


def test_duplicate_key_raises(achievement_registry):
    AchievementDef(
        key="dup",
        name="First",
        description="",
        threshold=lambda user: False,
        registry=achievement_registry,
    )
    with pytest.raises(ValueError, match="dup"):
        AchievementDef(
            key="dup",
            name="Second",
            description="",
            threshold=lambda user: False,
            registry=achievement_registry,
        )


def test_threshold_not_called_at_construction(achievement_registry):
    called = []
    AchievementDef(
        key="no_call",
        name="No Call",
        description="",
        threshold=lambda user: called.append(True) or False,
        registry=achievement_registry,
    )
    assert called == []


@pytest.mark.django_db
def test_check_achievements_creates_row(achievement_registry, django_user_model):
    user = django_user_model.objects.create_user(username="tester", password="x")
    AchievementDef(
        key="always",
        name="Always",
        description="Threshold always true",
        threshold=lambda u: True,
        registry=achievement_registry,
    )

    new_ones = check_achievements(user, reg=achievement_registry)

    assert len(new_ones) == 1
    assert new_ones[0].key == "always"
    assert Achievement.objects.filter(user=user, achievement_key="always").exists()


@pytest.mark.django_db
def test_check_achievements_not_awarded_twice(achievement_registry, django_user_model):
    user = django_user_model.objects.create_user(username="tester2", password="x")
    AchievementDef(
        key="once",
        name="Once",
        description="",
        threshold=lambda u: True,
        registry=achievement_registry,
    )

    check_achievements(user, reg=achievement_registry)
    new_ones = check_achievements(user, reg=achievement_registry)

    assert new_ones == []


@pytest.mark.django_db
def test_check_achievements_skips_unmet(achievement_registry, django_user_model):
    user = django_user_model.objects.create_user(username="tester3", password="x")
    AchievementDef(
        key="never",
        name="Never",
        description="",
        threshold=lambda u: False,
        registry=achievement_registry,
    )

    new_ones = check_achievements(user, reg=achievement_registry)

    assert new_ones == []
    assert not Achievement.objects.filter(user=user).exists()

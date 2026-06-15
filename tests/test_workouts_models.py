import pytest
from django.core.exceptions import ValidationError

from workouts.forms import CardioExerciseForm
from workouts.models import CardioExercise, Movement


@pytest.fixture
def cardio_movement(db):
    return Movement.objects.create(name="swimming", kind=Movement.CARDIO)


@pytest.mark.django_db
def test_cardio_model_clean_requires_distance_or_duration(cardio_movement):
    ex = CardioExercise(movement=cardio_movement)
    with pytest.raises(ValidationError):
        ex.clean()


@pytest.mark.django_db
def test_cardio_form_invalid_without_distance_or_duration(cardio_movement):
    form = CardioExerciseForm(
        data={
            "movement": cardio_movement.pk,
            "distance_0": "",
            "distance_1": "",
            "duration_0": "",
            "duration_1": "",
            "notes": "",
        }
    )
    assert not form.is_valid()
    assert "at least one" in str(form.errors).lower()


@pytest.mark.django_db
def test_cardio_form_valid_with_distance_only(cardio_movement):
    form = CardioExerciseForm(
        data={
            "movement": cardio_movement.pk,
            "distance_0": "5",
            "distance_1": "mile",
            "duration_0": "",
            "duration_1": "",
            "notes": "",
        }
    )
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_cardio_form_valid_with_duration_only(cardio_movement):
    form = CardioExerciseForm(
        data={
            "movement": cardio_movement.pk,
            "distance_0": "",
            "distance_1": "",
            "duration_0": "20",
            "duration_1": "0",
            "notes": "",
        }
    )
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_seed_movements_present():
    names = set(Movement.objects.values_list("name", flat=True))
    assert {"rowing", "running"} <= names

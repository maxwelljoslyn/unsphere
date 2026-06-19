from django.db import models
from django.conf import settings

from .fields import PintField


class Movement(models.Model):
    CARDIO = "cardio"
    STRENGTH = "strength"
    KIND_CHOICES = [(CARDIO, "Cardio"), (STRENGTH, "Strength")]

    name = models.CharField(max_length=100, unique=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)

    def __str__(self):
        return self.name


class Workout(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workouts"
    )
    date = models.DateTimeField()
    # IANA name of the zone the workout was logged in (e.g. "America/Los_Angeles").
    # `date` is stored as a UTC instant; this records where it happened so it's
    # always displayed in — and labeled with — that origin zone.
    timezone = models.CharField(max_length=64, default="UTC")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # NULL while the workout is a draft being built; set when the user confirms
    # it. Only confirmed workouts count toward gems and achievements, so a draft
    # can be assembled exercise-by-exercise without prematurely awarding anything.
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.user} — {self.date}"

    @property
    def is_draft(self) -> bool:
        return self.confirmed_at is None


class Exercise(models.Model):
    workout = models.ForeignKey(
        Workout, on_delete=models.CASCADE, related_name="%(class)ss"
    )
    movement = models.ForeignKey(
        Movement, on_delete=models.CASCADE, related_name="%(class)ss"
    )
    notes = models.TextField(blank=True)

    class Meta:
        abstract = True


class CardioExercise(Exercise):
    distance = PintField(null=True, blank=True)
    duration = PintField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(distance__isnull=False)
                | models.Q(duration__isnull=False),
                name="cardio_exercise_requires_distance_or_duration",
                violation_error_message="Enter at least one of distance or duration.",
            )
        ]

    def __str__(self):
        parts = [str(self.movement)]
        if self.distance is not None:
            parts.append(str(self.distance))
        if self.duration is not None:
            parts.append(str(self.duration))
        return " — ".join(parts)


class StrengthExercise(Exercise):
    sets = models.PositiveIntegerField()
    reps = models.PositiveIntegerField()
    weight = PintField(null=True, blank=True)

    def __str__(self):
        w = f" @ {self.weight}" if self.weight is not None else ""
        return f"{self.movement} — {self.sets}x{self.reps}{w}"

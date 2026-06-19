from zoneinfo import ZoneInfo

from django import forms
from django.conf import settings

from .fields import (
    DISTANCE_UNITS,
    WEIGHT_UNITS,
    PintFormField,
    PintTimeFormField,
)
from .models import CardioExercise, Movement, StrengthExercise, Workout


def _safe_zone(name):
    try:
        return ZoneInfo(name or settings.TIME_ZONE)
    except (KeyError, ValueError):
        return ZoneInfo(settings.TIME_ZONE)


class FeedbackForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Brief summary of the issue"}),
    )
    description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 6,
                "placeholder": "What happened? What did you expect instead?",
            }
        ),
    )


class WorkoutForm(forms.ModelForm):
    # Populated client-side from the browser's zone (see workout_form.html). The
    # datetime-local picker only gives a naive wall-clock time, so we pair it
    # with the zone that wall-clock was read in.
    timezone = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Workout
        fields = ["date", "notes", "timezone"]
        widgets = {
            "date": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                # How an existing value is shown in the <input>; matches the
                # value an <input type="datetime-local"> submits.
                format="%Y-%m-%dT%H:%M",
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Parse the "YYYY-MM-DDTHH:MM" value the datetime-local input submits.
        self.fields["date"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"]

        inst = self.instance
        if inst is not None and inst.pk and inst.date:
            # Show the picker in the zone the workout was logged in, so editing
            # round-trips the originally entered wall-clock time.
            zone = _safe_zone(inst.timezone)
            self.initial["date"] = inst.date.astimezone(zone).replace(tzinfo=None)
            self.initial["timezone"] = inst.timezone or settings.TIME_ZONE

    def clean(self):
        cleaned = super().clean()
        zone = _safe_zone(cleaned.get("timezone"))
        cleaned["timezone"] = zone.key  # normalize to what we actually resolved
        value = cleaned.get("date")
        if value is not None:
            # forms.DateTimeField already made the value aware in the server's
            # default zone (UTC) without shifting the wall-clock digits. Strip
            # that and re-anchor the typed wall-clock to the origin zone.
            wall_clock = value.replace(tzinfo=None)
            cleaned["date"] = wall_clock.replace(tzinfo=zone)
        return cleaned


class MovementForm(forms.ModelForm):
    class Meta:
        model = Movement
        fields = ["name", "kind"]


class CardioExerciseForm(forms.ModelForm):
    distance = PintFormField(DISTANCE_UNITS, required=False)
    duration = PintTimeFormField(required=False)

    class Meta:
        model = CardioExercise
        fields = ["movement", "distance", "duration", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["movement"].queryset = Movement.objects.filter(kind=Movement.CARDIO)


class StrengthExerciseForm(forms.ModelForm):
    weight = PintFormField(WEIGHT_UNITS, required=False)

    class Meta:
        model = StrengthExercise
        fields = ["movement", "sets", "reps", "weight", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["movement"].queryset = Movement.objects.filter(
            kind=Movement.STRENGTH
        )

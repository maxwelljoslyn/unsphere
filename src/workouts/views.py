from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .forms import CardioExerciseForm, MovementForm, StrengthExerciseForm, WorkoutForm
from .models import CardioExercise, Movement, StrengthExercise, Workout


@login_required
def workout_list(request):
    workouts = Workout.objects.filter(user=request.user)
    return render(request, "workouts/workout_list.html", {"workouts": workouts})


@login_required
def workout_create(request):
    if request.method == "POST":
        form = WorkoutForm(request.POST)
        if form.is_valid():
            workout = form.save(commit=False)
            workout.user = request.user
            workout.save()
            return redirect("workout-detail", pk=workout.pk)
    else:
        form = WorkoutForm()
    return render(request, "workouts/workout_form.html", {"form": form})


@login_required
def workout_detail(request, pk):
    workout = get_object_or_404(Workout, pk=pk, user=request.user)
    return render(
        request,
        "workouts/workout_detail.html",
        {
            "workout": workout,
            "cardio_exercises": workout.cardioexercises.all(),
            "strength_exercises": workout.strengthexercises.all(),
        },
    )


@login_required
def workout_edit(request, pk):
    workout = get_object_or_404(Workout, pk=pk, user=request.user)
    if request.method == "POST":
        form = WorkoutForm(request.POST, instance=workout)
        if form.is_valid():
            form.save()
            return redirect("workout-detail", pk=workout.pk)
    else:
        form = WorkoutForm(instance=workout)
    return render(
        request, "workouts/workout_form.html", {"form": form, "workout": workout}
    )


@login_required
def workout_delete(request, pk):
    workout = get_object_or_404(Workout, pk=pk, user=request.user)
    if request.method == "POST":
        workout.delete()
        return redirect("workout-list")
    return render(request, "workouts/workout_confirm_delete.html", {"workout": workout})


@login_required
@require_POST
def workout_confirm(request, pk):
    """Confirm a draft workout so it starts counting toward gems/achievements.

    Idempotent: confirming an already-confirmed workout leaves its timestamp
    untouched. The gem/achievement evaluation isn't done here — it rides the
    normal middleware pass over this very request, which now sees the workout as
    confirmed, so celebrations and the gem toast are injected as usual.
    """
    workout = get_object_or_404(Workout, pk=pk, user=request.user)
    if workout.confirmed_at is None:
        workout.confirmed_at = timezone.now()
        workout.save(update_fields=["confirmed_at"])
    if request.headers.get("HX-Request") == "true":
        return render(request, "workouts/_workout_status.html", {"workout": workout})
    return redirect("workout-detail", pk=workout.pk)


# ---------------------------------------------------------------------------
# Exercises (HTMX-driven, on the workout detail page)
# ---------------------------------------------------------------------------


@login_required
def cardio_exercise_add(request, workout_pk):
    workout = get_object_or_404(Workout, pk=workout_pk, user=request.user)
    if request.method == "POST":
        form = CardioExerciseForm(request.POST)
        if form.is_valid():
            ex = form.save(commit=False)
            ex.workout = workout
            ex.save()
            return render(
                request,
                "workouts/_exercise_added.html",
                {
                    "workout": workout,
                    "ex": ex,
                    "ex_type": "cardio",
                },
            )
        return render(
            request, "workouts/_cardio_form.html", {"workout": workout, "form": form}
        )
    return render(
        request,
        "workouts/_cardio_form.html",
        {
            "workout": workout,
            "form": CardioExerciseForm(),
        },
    )


@login_required
def cardio_exercise_edit(request, pk):
    ex = get_object_or_404(CardioExercise, pk=pk, workout__user=request.user)
    if request.method == "POST":
        form = CardioExerciseForm(request.POST, instance=ex)
        if form.is_valid():
            form.save()
            return render(request, "workouts/_cardio_exercise.html", {"ex": ex})
        return render(
            request, "workouts/_cardio_edit_form.html", {"ex": ex, "form": form}
        )
    form = CardioExerciseForm(instance=ex)
    return render(request, "workouts/_cardio_edit_form.html", {"ex": ex, "form": form})


@login_required
@require_http_methods(["DELETE"])
def cardio_exercise_delete(request, pk):
    ex = get_object_or_404(CardioExercise, pk=pk, workout__user=request.user)
    ex.delete()
    return HttpResponse("")


@login_required
def strength_exercise_add(request, workout_pk):
    workout = get_object_or_404(Workout, pk=workout_pk, user=request.user)
    if request.method == "POST":
        form = StrengthExerciseForm(request.POST)
        if form.is_valid():
            ex = form.save(commit=False)
            ex.workout = workout
            ex.save()
            return render(
                request,
                "workouts/_exercise_added.html",
                {
                    "workout": workout,
                    "ex": ex,
                    "ex_type": "strength",
                },
            )
        return render(
            request, "workouts/_strength_form.html", {"workout": workout, "form": form}
        )
    return render(
        request,
        "workouts/_strength_form.html",
        {
            "workout": workout,
            "form": StrengthExerciseForm(),
        },
    )


@login_required
def strength_exercise_edit(request, pk):
    ex = get_object_or_404(StrengthExercise, pk=pk, workout__user=request.user)
    if request.method == "POST":
        form = StrengthExerciseForm(request.POST, instance=ex)
        if form.is_valid():
            form.save()
            return render(request, "workouts/_strength_exercise.html", {"ex": ex})
        return render(
            request, "workouts/_strength_edit_form.html", {"ex": ex, "form": form}
        )
    form = StrengthExerciseForm(instance=ex)
    return render(
        request, "workouts/_strength_edit_form.html", {"ex": ex, "form": form}
    )


@login_required
@require_http_methods(["DELETE"])
def strength_exercise_delete(request, pk):
    ex = get_object_or_404(StrengthExercise, pk=pk, workout__user=request.user)
    ex.delete()
    return HttpResponse("")


# ---------------------------------------------------------------------------
# Movements
# ---------------------------------------------------------------------------


@login_required
def movement_list(request):
    movements = Movement.objects.all().order_by("kind", "name")
    return render(request, "workouts/movement_list.html", {"movements": movements})


@login_required
def movement_create(request):
    if request.method == "POST":
        form = MovementForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("movement-list")
    else:
        form = MovementForm()
    return render(request, "workouts/movement_form.html", {"form": form})


@login_required
def movement_edit(request, pk):
    movement = get_object_or_404(Movement, pk=pk)
    if request.method == "POST":
        form = MovementForm(request.POST, instance=movement)
        if form.is_valid():
            form.save()
            return redirect("movement-list")
    else:
        form = MovementForm(instance=movement)
    return render(
        request, "workouts/movement_form.html", {"form": form, "movement": movement}
    )


@login_required
def movement_delete(request, pk):
    movement = get_object_or_404(Movement, pk=pk)
    if request.method == "POST":
        movement.delete()
        return redirect("movement-list")
    return render(
        request, "workouts/movement_confirm_delete.html", {"movement": movement}
    )

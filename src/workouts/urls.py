from django.urls import path

from . import views

urlpatterns = [
    path("workouts/", views.workout_list, name="workout-list"),
    path("workouts/new/", views.workout_create, name="workout-create"),
    path("workouts/<int:pk>/", views.workout_detail, name="workout-detail"),
    path("workouts/<int:pk>/edit/", views.workout_edit, name="workout-edit"),
    path("workouts/<int:pk>/confirm/", views.workout_confirm, name="workout-confirm"),
    path("workouts/<int:pk>/delete/", views.workout_delete, name="workout-delete"),
    path(
        "workouts/<int:workout_pk>/cardio/add/",
        views.cardio_exercise_add,
        name="cardio-exercise-add",
    ),
    path(
        "cardio/<int:pk>/edit/", views.cardio_exercise_edit, name="cardio-exercise-edit"
    ),
    path(
        "cardio/<int:pk>/delete/",
        views.cardio_exercise_delete,
        name="cardio-exercise-delete",
    ),
    path(
        "workouts/<int:workout_pk>/strength/add/",
        views.strength_exercise_add,
        name="strength-exercise-add",
    ),
    path(
        "strength/<int:pk>/edit/",
        views.strength_exercise_edit,
        name="strength-exercise-edit",
    ),
    path(
        "strength/<int:pk>/delete/",
        views.strength_exercise_delete,
        name="strength-exercise-delete",
    ),
    path("movements/", views.movement_list, name="movement-list"),
    path("movements/new/", views.movement_create, name="movement-create"),
    path("movements/<int:pk>/edit/", views.movement_edit, name="movement-edit"),
    path("movements/<int:pk>/delete/", views.movement_delete, name="movement-delete"),
    path("feedback/", views.feedback, name="feedback"),
]

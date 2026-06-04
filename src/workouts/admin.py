from django.contrib import admin

from .models import CardioExercise, Movement, StrengthExercise, Workout


@admin.register(Movement)
class MovementAdmin(admin.ModelAdmin):
    list_display = ("name", "kind")
    list_filter = ("kind",)
    search_fields = ("name",)


@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):
    list_display = ("date", "user", "created_at")
    list_filter = ("user",)
    date_hierarchy = "date"


@admin.register(CardioExercise)
class CardioExerciseAdmin(admin.ModelAdmin):
    list_display = ("workout", "movement", "distance", "duration")
    list_filter = ("movement",)


@admin.register(StrengthExercise)
class StrengthExerciseAdmin(admin.ModelAdmin):
    list_display = ("workout", "movement", "sets", "reps", "weight")
    list_filter = ("movement",)

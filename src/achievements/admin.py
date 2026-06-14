from django.contrib import admin

from .models import Achievement


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("user", "achievement_key", "earned_at", "acknowledged_at")
    list_filter = ("achievement_key", "user")
    readonly_fields = ("earned_at",)

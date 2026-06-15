from django.contrib import admin

from .models import GemTransaction


@admin.register(GemTransaction)
class GemTransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "rule_key", "category", "created_at")
    list_filter = ("rule_key", "category", "user")
    readonly_fields = ("created_at",)

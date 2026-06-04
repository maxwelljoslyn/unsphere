from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

User = get_user_model()


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "email_confirmed", "is_superuser", "is_staff")
    list_filter = ("email_confirmed", "is_superuser", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (("Unsphere", {"fields": ("email_confirmed",)}),)

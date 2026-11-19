from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "is_manager",
        "email_verified",
        "is_active",
        "is_staff",
    )

    list_filter = (
        "is_manager",
        "email_verified",
        "is_active",
        "is_staff",
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            "Права в сервисе рассылок",
            {
                "fields": (
                    "is_manager",
                    "email_verified",
                )
            },
        ),
    )

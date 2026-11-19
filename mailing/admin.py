from django.contrib import admin

from .models import Recipient, Message, Mailing, MailingAttempt


@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "full_name", "owner")
    search_fields = ("email", "full_name")
    list_filter = ("owner",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "owner")
    search_fields = ("subject",)
    list_filter = ("owner",)


@admin.register(Mailing)
class MailingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "start_time",
        "end_time",
        "status",
        "owner",
        "is_active",
    )
    list_filter = ("status", "is_active", "owner")
    search_fields = ("message__subject",)


@admin.register(MailingAttempt)
class MailingAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "mailing",
        "recipient_email",
        "status",
        "attempt_time",
    )
    list_filter = ("status", "attempt_time")
    search_fields = ("recipient_email",)

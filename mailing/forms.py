from django import forms
from django.utils import timezone

from .models import Recipient, Message, Mailing


class RecipientForm(forms.ModelForm):
    """Форма создания и редактирования получателя."""

    class Meta:
        model = Recipient
        fields = ["email", "full_name", "comment"]
        widgets = {
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "Email получателя",
            }),
            "full_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ф. И. О.",
            }),
            "comment": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
            }),
        }


class MessageForm(forms.ModelForm):
    """Форма создания и редактирования сообщения."""

    class Meta:
        model = Message
        fields = ["subject", "body"]
        widgets = {
            "subject": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Тема письма",
            }),
            "body": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 6,
            }),
        }


class MailingForm(forms.ModelForm):
    """Форма создания и редактирования рассылки."""

    class Meta:
        model = Mailing
        fields = ["start_time", "end_time", "message", "recipients"]
        widgets = {
            "start_time": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local",
            }),
            "end_time": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local",
            }),
            "message": forms.Select(attrs={
                "class": "form-control",
            }),
            "recipients": forms.SelectMultiple(attrs={
                "class": "form-control",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user

        if user is not None:
            self.fields["message"].queryset = Message.objects.filter(
                owner=user
            )
            self.fields["recipients"].queryset = Recipient.objects.filter(
                owner=user
            )

    def clean(self):
        cleaned_data = super().clean()

        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if start_time and start_time < timezone.now():
            self.add_error(
                "start_time",
                "Дата начала рассылки не может быть в прошлом."
            )

        if start_time and end_time and start_time >= end_time:
            self.add_error(
                "end_time",
                "Дата окончания должна быть позже даты начала."
            )

        return cleaned_data

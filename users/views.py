from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from .forms import RegistrationForm
from .models import User


def register(request):
    """Регистрация нового пользователя."""

    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            confirmation_url = request.build_absolute_uri(
                reverse(
                    "users:activate",
                    kwargs={"uidb64": uid, "token": token},
                )
            )

            send_mail(
                subject="Подтверждение регистрации",
                message=(
                    f"Здравствуйте, {user.username}!\n\n"
                    f"Для подтверждения регистрации перейдите по ссылке:\n"
                    f"{confirmation_url}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            messages.success(
                request,
                "Регистрация выполнена! Проверьте почту "
                "в терминале для подтверждения email."
            )
            return redirect("users:login")

    else:
        form = RegistrationForm()

    return render(request, "users/register.html", {"form": form})


def activate(request, uidb64, token):
    """Подтверждение электронной почты."""

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_object_or_404(User, pk=uid)
    except (TypeError, ValueError, OverflowError):
        user = None

    if (
        user is not None
        and default_token_generator.check_token(user, token)
    ):
        user.email_verified = True
        user.is_active = True
        user.save(update_fields=["email_verified", "is_active"])

        messages.success(
            request,
            "Электронная почта подтверждена. Теперь вы можете войти."
        )
        return redirect("users:login")

    return HttpResponse(
        "Ссылка подтверждения недействительна или устарела.",
        status=400,
    )

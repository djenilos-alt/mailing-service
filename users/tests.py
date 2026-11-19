from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


User = get_user_model()


class UserRegistrationTests(TestCase):

    def test_register_page(self):
        """Проверяет открытие страницы регистрации."""
        response = self.client.get(reverse("users:register"))

        self.assertEqual(response.status_code, 200)

    def test_successful_registration(self):
        """Проверяет регистрацию нового пользователя."""
        response = self.client.post(
            reverse("users:register"),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password1": "StrongPassword123!",
                "password2": "StrongPassword123!",
            }
        )

        self.assertRedirects(response, reverse("users:login"))

        user = User.objects.get(username="newuser")

        self.assertEqual(user.email, "newuser@example.com")
        self.assertFalse(user.is_active)
        self.assertFalse(user.email_verified)

    def test_confirmation_email_sent(self):
        """Проверяет отправку письма подтверждения."""
        self.client.post(
            reverse("users:register"),
            {
                "username": "mailuser",
                "email": "mailuser@example.com",
                "password1": "StrongPassword123!",
                "password2": "StrongPassword123!",
            }
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            "Подтверждение регистрации"
        )
        self.assertEqual(
            mail.outbox[0].to,
            ["mailuser@example.com"]
        )

    def test_successful_activation(self):
        """Проверяет активацию пользователя по действительной ссылке."""
        user = User.objects.create_user(
            username="inactiveuser",
            email="inactive@example.com",
            password="StrongPassword123!",
            is_active=False,
            email_verified=False,
        )

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        response = self.client.get(
            reverse(
                "users:activate",
                kwargs={"uidb64": uid, "token": token}
            )
        )

        self.assertRedirects(response, reverse("users:login"))

        user.refresh_from_db()

        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)

    def test_invalid_activation_token(self):
        """Проверяет отклонение недействительного токена."""
        user = User.objects.create_user(
            username="invaliduser",
            email="invalid@example.com",
            password="StrongPassword123!",
            is_active=False,
            email_verified=False,
        )

        uid = urlsafe_base64_encode(force_bytes(user.pk))

        response = self.client.get(
            reverse(
                "users:activate",
                kwargs={
                    "uidb64": uid,
                    "token": "invalid-token"
                }
            )
        )

        self.assertEqual(response.status_code, 400)

        user.refresh_from_db()

        self.assertFalse(user.is_active)
        self.assertFalse(user.email_verified)

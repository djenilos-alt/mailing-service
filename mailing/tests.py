from .models import Mailing, MailingAttempt, Message, Recipient
from unittest.mock import patch
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import Mailing, Message, Recipient


User = get_user_model()


class MailingModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPassword123!"
        )

        self.recipient = Recipient.objects.create(
            email="recipient@example.com",
            full_name="Тестовый получатель",
            owner=self.user
        )

        self.message = Message.objects.create(
            subject="Тестовая тема",
            body="Текст тестового письма",
            owner=self.user
        )

    def create_mailing(self, start_time, end_time):
        mailing = Mailing(
            start_time=start_time,
            end_time=end_time,
            message=self.message,
            owner=self.user
        )
        mailing.save()
        mailing.recipients.add(self.recipient)
        return mailing

    def test_create_mailing(self):
        """Проверяет создание рассылки и связь с получателем."""
        now = timezone.now()

        mailing = self.create_mailing(
            now + timedelta(hours=1),
            now + timedelta(hours=2)
        )

        self.assertEqual(Mailing.objects.count(), 1)
        self.assertEqual(mailing.recipients.count(), 1)
        self.assertEqual(mailing.status, Mailing.Status.CREATED)

    def test_created_status(self):
        """Проверяет статус до начала рассылки."""
        now = timezone.now()

        mailing = self.create_mailing(
            now + timedelta(hours=1),
            now + timedelta(hours=2)
        )

        mailing.update_status()

        self.assertEqual(mailing.status, Mailing.Status.CREATED)

    def test_started_status(self):
        """Проверяет статус во время рассылки."""
        now = timezone.now()

        mailing = self.create_mailing(
            now - timedelta(hours=1),
            now + timedelta(hours=1)
        )

        mailing.update_status()

        self.assertEqual(mailing.status, Mailing.Status.STARTED)

    def test_completed_status(self):
        """Проверяет статус после окончания рассылки."""
        now = timezone.now()

        mailing = self.create_mailing(
            now - timedelta(hours=2),
            now - timedelta(hours=1)
        )

        mailing.update_status()

        self.assertEqual(mailing.status, Mailing.Status.COMPLETED)

    def test_invalid_dates(self):
        """Проверяет запрет окончания раньше начала."""
        now = timezone.now()

        mailing = Mailing(
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=1),
            message=self.message,
            owner=self.user
        )

        with self.assertRaises(ValidationError):
            mailing.full_clean()

    def test_past_start_time(self):
        """Проверяет запрет создания рассылки с прошлой датой начала."""
        now = timezone.now()

        mailing = Mailing(
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
            message=self.message,
            owner=self.user
        )

        with self.assertRaises(ValidationError):
            mailing.full_clean()

    @patch("mailing.services.send_mail", return_value=1)
    def test_successful_mailing(self, mock_send_mail):
        """Проверяет успешную отправку письма."""
        from .services import send_mailing

        now = timezone.now()
        mailing = self.create_mailing(
            now - timedelta(hours=1),
            now + timedelta(hours=1)
        )

        result = send_mailing(mailing)

        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failed_count"], 0)

        attempt = MailingAttempt.objects.get(mailing=mailing)
        self.assertEqual(
            attempt.status,
            MailingAttempt.Status.SUCCESS
        )
        self.assertEqual(
            attempt.recipient_email,
            self.recipient.email
        )
        mock_send_mail.assert_called_once()

    @patch(
        "mailing.services.send_mail",
        side_effect=Exception("Ошибка тестовой отправки")
    )
    def test_failed_mailing(self, mock_send_mail):
        """Проверяет обработку ошибки отправки."""
        from .services import send_mailing

        now = timezone.now()
        mailing = self.create_mailing(
            now - timedelta(hours=1),
            now + timedelta(hours=1)
        )

        result = send_mailing(mailing)

        self.assertEqual(result["success_count"], 0)
        self.assertEqual(result["failed_count"], 1)

        attempt = MailingAttempt.objects.get(mailing=mailing)
        self.assertEqual(
            attempt.status,
            MailingAttempt.Status.FAILED
        )
        self.assertEqual(
            attempt.server_response,
            "Ошибка тестовой отправки"
        )

    def test_disabled_mailing(self):
        """Проверяет запрет отправки отключённой рассылки."""
        from .services import send_mailing

        now = timezone.now()
        mailing = self.create_mailing(
            now - timedelta(hours=1),
            now + timedelta(hours=1)
        )
        mailing.is_active = False
        mailing.save()

        with self.assertRaises(ValidationError):
            send_mailing(mailing)

        self.assertEqual(
            MailingAttempt.objects.filter(mailing=mailing).count(),
            0
        )

    def test_mailing_outside_period(self):
        """Проверяет запрет отправки после окончания рассылки."""
        from .services import send_mailing

        now = timezone.now()
        mailing = self.create_mailing(
            now - timedelta(hours=2),
            now - timedelta(hours=1)
        )

        with self.assertRaises(ValidationError):
            send_mailing(mailing)

        self.assertEqual(
            MailingAttempt.objects.filter(mailing=mailing).count(),
            0
        )
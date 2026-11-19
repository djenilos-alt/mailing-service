from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from mailing.models import Mailing, Message, Recipient


User = get_user_model()


class ManagerAccessTests(TestCase):

    def setUp(self):
        self.manager = User.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="ManagerPass123!",
            is_manager=True,
            email_verified=True,
        )

        self.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="UserPass123!",
            email_verified=True,
        )

        self.message = Message.objects.create(
            subject="Тестовая тема",
            body="Тестовое сообщение",
            owner=self.user,
        )

        self.recipient = Recipient.objects.create(
            email="recipient@example.com",
            full_name="Тестовый получатель",
            comment="Тест",
            owner=self.user,
        )

        self.mailing = Mailing.objects.create(
            start_time="2026-11-20T10:00:00+00:00",
            end_time="2026-11-21T10:00:00+00:00",
            message=self.message,
            owner=self.user,
        )
        self.mailing.recipients.add(self.recipient)

    def test_anonymous_user_redirected_from_manager_dashboard(self):
        response = self.client.get(
            reverse("service:manager_dashboard")
        )
        self.assertEqual(response.status_code, 302)

    def test_regular_user_cannot_open_manager_dashboard(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("service:manager_dashboard")
        )

        self.assertEqual(response.status_code, 403)

    def test_manager_can_open_manager_dashboard(self):
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("service:manager_dashboard")
        )

        self.assertEqual(response.status_code, 200)

    def test_regular_user_cannot_open_manager_users(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("service:manager_users")
        )

        self.assertEqual(response.status_code, 403)

    def test_manager_can_open_manager_users(self):
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("service:manager_users")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "manager")
        self.assertContains(response, "user")

    def test_manager_can_open_all_mailings(self):
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("service:manager_mailings")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Тестовая тема")

    def test_regular_user_cannot_disable_mailing(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "service:manager_disable_mailing",
                args=[self.mailing.pk],
            )
        )

        self.assertEqual(response.status_code, 403)
        self.mailing.refresh_from_db()
        self.assertTrue(self.mailing.is_active)

    def test_manager_can_disable_mailing(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse(
                "service:manager_disable_mailing",
                args=[self.mailing.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("service:manager_mailings"),
        )

        self.mailing.refresh_from_db()
        self.assertFalse(self.mailing.is_active)

    def test_manager_can_block_and_unblock_user(self):
        self.client.force_login(self.manager)

        url = reverse(
            "service:manager_toggle_user",
            args=[self.user.pk],
        )

        response = self.client.post(url)

        self.assertRedirects(
            response,
            reverse("service:manager_users"),
        )

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

        response = self.client.post(url)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_manager_cannot_block_themselves(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse(
                "service:manager_toggle_user",
                args=[self.manager.pk],
            )
        )

        self.manager.refresh_from_db()
        self.assertTrue(self.manager.is_active)

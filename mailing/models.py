from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Recipient(models.Model):
    """Получатель рассылки."""

    email = models.EmailField(
        unique=True,
        verbose_name="Email"
    )
    full_name = models.CharField(
        max_length=255,
        verbose_name="Ф. И. О."
    )
    comment = models.TextField(
        blank=True,
        verbose_name="Комментарий"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipients",
        verbose_name="Владелец"
    )

    class Meta:
        verbose_name = "Получатель"
        verbose_name_plural = "Получатели"
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.email})"


class Message(models.Model):
    """Сообщение для рассылки."""

    subject = models.CharField(
        max_length=255,
        verbose_name="Тема письма"
    )
    body = models.TextField(
        verbose_name="Тело письма"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Владелец"
    )

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ["subject"]

    def __str__(self):
        return self.subject


class Mailing(models.Model):
    """Рассылка сообщений."""

    class Status(models.TextChoices):
        CREATED = "Создана", "Создана"
        STARTED = "Запущена", "Запущена"
        COMPLETED = "Завершена", "Завершена"

    start_time = models.DateTimeField(
        verbose_name="Дата и время начала"
    )
    end_time = models.DateTimeField(
        verbose_name="Дата и время окончания"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
        verbose_name="Статус"
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.PROTECT,
        related_name="mailings",
        verbose_name="Сообщение"
    )
    recipients = models.ManyToManyField(
        Recipient,
        related_name="mailings",
        verbose_name="Получатели"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mailings",
        verbose_name="Владелец"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активна"
    )

    class Meta:
        verbose_name = "Рассылка"
        verbose_name_plural = "Рассылки"
        ordering = ["-start_time"]

    def __str__(self):
        return f"Рассылка №{self.pk}"

    def clean(self):
        super().clean()

        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError({
                    "end_time": "Дата окончания должна быть позже даты начала."
                })

            if not self.pk and self.start_time < timezone.now():
                raise ValidationError({
                    "start_time": "Дата начала не может быть в прошлом."
                })

    def update_status(self):
        """Обновляет статус рассылки в зависимости от текущего времени."""

        now = timezone.now()

        if now < self.start_time:
            new_status = self.Status.CREATED
        elif now <= self.end_time:
            new_status = self.Status.STARTED
        else:
            new_status = self.Status.COMPLETED

        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=["status"])


class MailingAttempt(models.Model):
    """Попытка отправки сообщения."""

    class Status(models.TextChoices):
        SUCCESS = "Успешно", "Успешно"
        FAILED = "Не успешно", "Не успешно"

    attempt_time = models.DateTimeField(
        default=timezone.now,
        verbose_name="Дата и время попытки"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        verbose_name="Статус"
    )
    server_response = models.TextField(
        blank=True,
        verbose_name="Ответ почтового сервера"
    )
    mailing = models.ForeignKey(
        Mailing,
        on_delete=models.CASCADE,
        related_name="attempts",
        verbose_name="Рассылка"
    )
    recipient_email = models.EmailField(
        verbose_name="Email получателя"
    )

    class Meta:
        verbose_name = "Попытка рассылки"
        verbose_name_plural = "Попытки рассылок"
        ordering = ["-attempt_time"]

    def __str__(self):
        return f"{self.mailing} — {self.status}"

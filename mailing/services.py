from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail

from .models import Mailing, MailingAttempt


def send_mailing(mailing):
    """Отправляет письма получателям и сохраняет историю попыток."""

    mailing.update_status()

    if not mailing.is_active:
        raise ValidationError("Рассылка отключена.")

    if mailing.status != Mailing.Status.STARTED:
        raise ValidationError(
            "Отправлять письма можно только в период действия рассылки."
        )

    recipients = mailing.recipients.all()

    if not recipients.exists():
        raise ValidationError("В рассылке нет получателей.")

    success_count = 0
    failed_count = 0
    attempts = []

    for recipient in recipients:
        try:
            result = send_mail(
                subject=mailing.message.subject,
                message=mailing.message.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                fail_silently=False,
            )

            if result == 1:
                status = MailingAttempt.Status.SUCCESS
                response = "Письмо успешно передано почтовому backend."
                success_count += 1
            else:
                status = MailingAttempt.Status.FAILED
                response = "Почтовый backend не подтвердил отправку."
                failed_count += 1

        except Exception as error:
            status = MailingAttempt.Status.FAILED
            response = str(error)
            failed_count += 1

        attempts.append(
            MailingAttempt(
                mailing=mailing,
                recipient_email=recipient.email,
                status=status,
                server_response=response,
            )
        )

    # Сохраняем все попытки одним пакетным запросом.
    MailingAttempt.objects.bulk_create(attempts)

    return {
        "success_count": success_count,
        "failed_count": failed_count,
    }

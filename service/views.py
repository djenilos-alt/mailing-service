from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.views.generic import ListView, TemplateView
from django.db.models import Count, Q
from django.core.exceptions import PermissionDenied
from django.core.cache import cache
from django.utils.cache import patch_cache_control

from mailing.models import Mailing, MailingAttempt, Recipient


def get_attempt_stats(queryset, cache_key):
    """Возвращает статистику попыток отправки с использованием кэша."""

    return cache.get_or_set(
        cache_key,
        lambda: queryset.aggregate(
            total_attempts=Count("pk"),
            successful_attempts=Count(
                "pk",
                filter=Q(status=MailingAttempt.Status.SUCCESS),
            ),
            failed_attempts=Count(
                "pk",
                filter=Q(status=MailingAttempt.Status.FAILED),
            ),
        ),
        timeout=30,
    )

class PrivateCacheMixin:
    """Разрешает браузеру временно кэшировать персональные страницы."""

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        patch_cache_control(
            response,
            private=True,
            max_age=30,
            must_revalidate=True,
        )
        return response

class HomeView(PrivateCacheMixin, LoginRequiredMixin, TemplateView):
    template_name = "service/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user

        # Получаем только рассылки текущего пользователя
        mailings = Mailing.objects.filter(owner=user)

        # Обновляем статусы рассылок
        for mailing in mailings:
            mailing.update_status()

        # Получаем статистику
        context["total_mailings"] = mailings.count()

        context["active_mailings"] = mailings.filter(
            status=Mailing.Status.STARTED,
            is_active=True,
        ).count()

        context["total_recipients"] = Recipient.objects.filter(
            owner=user
        ).count()

        attempt_stats = get_attempt_stats(
            MailingAttempt.objects.filter(mailing__owner=user),
            f"home_attempt_stats_{user.pk}",
        )

        context.update(attempt_stats)
        context["sent_messages"] = attempt_stats["successful_attempts"]

        # Последние пять рассылок
        context["recent_mailings"] = (
            mailings.select_related("message")
            .order_by("-start_time")[:5]
        )

        return context

class ManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Доступ только авторизованным менеджерам."""

    def test_func(self):
        return self.request.user.is_manager


class ManagerDashboardView(PrivateCacheMixin, ManagerRequiredMixin, TemplateView):
    """Главная страница менеджера."""

    template_name = "service/manager_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        mailings = Mailing.objects.all()

        for mailing in mailings:
            mailing.update_status()

        context["total_mailings"] = mailings.count()
        context["active_mailings"] = mailings.filter(
            status=Mailing.Status.STARTED,
            is_active=True,
        ).count()
        context["total_recipients"] = Recipient.objects.count()
        context["total_users"] = get_user_model().objects.count()
        attempt_stats = get_attempt_stats(
            MailingAttempt.objects.all(),
            "manager_attempt_stats",
        )

        context.update(attempt_stats)
        context["sent_messages"] = attempt_stats["successful_attempts"]

        return context


class ManagerMailingListView(PrivateCacheMixin, ManagerRequiredMixin, ListView):
    """Список всех рассылок."""

    model = Mailing
    template_name = "service/manager_mailings.html"
    context_object_name = "mailings"

    def get_queryset(self):
        queryset = (
            Mailing.objects
            .select_related("owner", "message")
            .prefetch_related("recipients")
            .order_by("-start_time")
        )

        for mailing in queryset:
            mailing.update_status()

        return queryset


class ManagerRecipientListView(PrivateCacheMixin, ManagerRequiredMixin, ListView):
    """Список всех получателей."""

    model = Recipient
    template_name = "service/manager_recipients.html"
    context_object_name = "recipients"

    def get_queryset(self):
        return Recipient.objects.select_related("owner").order_by("email")


class ManagerUserListView(PrivateCacheMixin, ManagerRequiredMixin, ListView):
    """Список всех пользователей."""

    model = get_user_model()
    template_name = "service/manager_users.html"
    context_object_name = "users"

    def get_queryset(self):
        return get_user_model().objects.order_by("username")


@login_required
@require_POST
def manager_toggle_user(request, pk):
    """Блокировка или разблокировка обычного пользователя."""

    if not request.user.is_manager:
        raise PermissionDenied

    user = get_object_or_404(get_user_model(), pk=pk)

    if user.pk == request.user.pk:
        messages.error(request, "Нельзя заблокировать собственную учётную запись.")
    elif user.is_superuser or user.is_staff or user.is_manager:
        messages.error(
            request,
            "Нельзя блокировать администратора или другого менеджера.",
        )
    else:
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])

        if user.is_active:
            messages.success(request, f"Пользователь {user.username} разблокирован.")
        else:
            messages.success(request, f"Пользователь {user.username} заблокирован.")

    return redirect("service:manager_users")


@login_required
@require_POST
def manager_disable_mailing(request, pk):
    """Отключение рассылки менеджером."""

    if not request.user.is_manager:
        raise PermissionDenied

    mailing = get_object_or_404(Mailing, pk=pk)
    mailing.is_active = False
    mailing.save(update_fields=["is_active"])

    messages.success(request, f"Рассылка №{mailing.pk} отключена.")

    return redirect("service:manager_mailings")

from django.urls import path

from . import views

app_name = "service"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),

    # Раздел менеджера
    path(
        "manager/",
        views.ManagerDashboardView.as_view(),
        name="manager_dashboard",
    ),
    path(
        "manager/mailings/",
        views.ManagerMailingListView.as_view(),
        name="manager_mailings",
    ),
    path(
        "manager/recipients/",
        views.ManagerRecipientListView.as_view(),
        name="manager_recipients",
    ),
    path(
        "manager/users/",
        views.ManagerUserListView.as_view(),
        name="manager_users",
    ),
    path(
        "manager/users/<int:pk>/toggle/",
        views.manager_toggle_user,
        name="manager_toggle_user",
    ),
    path(
        "manager/mailings/<int:pk>/disable/",
        views.manager_disable_mailing,
        name="manager_disable_mailing",
    ),
]

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("", include("service.urls")),
    path("admin/", admin.site.urls),
    path("mailing/", include("mailing.urls")),
    path("users/", include("users.urls")),
]

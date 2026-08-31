from django.urls import path

from . import views

app_name = "prospecting"

urlpatterns = [
    path("health/", views.health_check, name="health"),
]

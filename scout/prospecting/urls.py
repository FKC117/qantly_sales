from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "prospecting"

router = DefaultRouter()
router.register("companies", views.CompanyViewSet, basename="company")
router.register("jobs", views.JobPostingViewSet, basename="job")
router.register("prospects", views.ProspectViewSet, basename="prospect")
router.register("contacts", views.ContactViewSet, basename="contact")
router.register("outreach", views.OutreachViewSet, basename="outreach")
router.register("activities", views.ProspectActivityViewSet, basename="activity")

urlpatterns = [
    path("health/", views.health_check, name="health"),
    path("", include(router.urls)),
]

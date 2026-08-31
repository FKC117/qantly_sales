from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "prospecting"

router = DefaultRouter()
router.register("search-profiles", views.SearchProfileViewSet, basename="search-profile")
router.register("search-roles", views.SearchRoleViewSet, basename="search-role")
router.register("search-signals", views.SearchSignalViewSet, basename="search-signal")
router.register("search-locations", views.SearchLocationViewSet, basename="search-location")
router.register("search-industries", views.SearchIndustryViewSet, basename="search-industry")
router.register("companies", views.CompanyViewSet, basename="company")
router.register("jobs", views.JobPostingViewSet, basename="job")
router.register("prospects", views.ProspectViewSet, basename="prospect")
router.register("contacts", views.ContactViewSet, basename="contact")
router.register("outreach", views.OutreachEmailViewSet, basename="outreach")
router.register("events", views.ProspectEventViewSet, basename="event")

urlpatterns = [
    path("health/", views.health_check, name="health"),
    path("", include(router.urls)),
]

from django.contrib import admin

from .models import (
    Company,
    Contact,
    JobPosting,
    OutreachEmail,
    Prospect,
    ProspectEvent,
    SearchIndustry,
    SearchLocation,
    SearchProfile,
    SearchRole,
    SearchSignal,
)


class SearchRoleInline(admin.TabularInline):
    model = SearchRole
    extra = 0


class SearchSignalInline(admin.TabularInline):
    model = SearchSignal
    extra = 0


class SearchLocationInline(admin.TabularInline):
    model = SearchLocation
    extra = 0


class SearchIndustryInline(admin.TabularInline):
    model = SearchIndustry
    extra = 0


@admin.register(SearchProfile)
class SearchProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "freshness_days", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    inlines = (SearchRoleInline, SearchSignalInline, SearchLocationInline, SearchIndustryInline)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "domain", "industry", "country", "updated_at")
    search_fields = ("name", "domain", "industry", "country")
    list_filter = ("industry", "country")


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "source", "location", "status", "posted_at", "discovered_at")
    search_fields = ("title", "company__name", "source", "location")
    list_filter = ("status", "source")
    autocomplete_fields = ("company",)


@admin.register(Prospect)
class ProspectAdmin(admin.ModelAdmin):
    list_display = ("company", "fit_score", "priority", "status", "created_at")
    search_fields = ("company__name", "fit_reason")
    list_filter = ("priority", "status")
    autocomplete_fields = ("company", "job_posting")


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "job_title", "email", "verification_status")
    search_fields = ("name", "company__name", "job_title", "email")
    list_filter = ("verification_status",)
    autocomplete_fields = ("company",)


@admin.register(OutreachEmail)
class OutreachEmailAdmin(admin.ModelAdmin):
    list_display = ("subject", "prospect", "contact", "status", "reply_status", "approved_at", "sent_at")
    search_fields = ("subject", "prospect__company__name", "contact__name")
    list_filter = ("status", "reply_status")
    autocomplete_fields = ("prospect", "contact", "approved_by")


@admin.register(ProspectEvent)
class ProspectEventAdmin(admin.ModelAdmin):
    list_display = ("prospect", "event_type", "created_at")
    search_fields = ("prospect__company__name",)
    list_filter = ("event_type",)
    autocomplete_fields = ("prospect",)
    readonly_fields = ("created_at",)

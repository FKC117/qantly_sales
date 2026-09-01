from django.contrib import admin
from import_export import fields, resources
from import_export.admin import ExportMixin

from .models import (
    Company,
    Contact,
    JobPosting,
    OutreachEmail,
    Prospect,
    ProspectEvent,
    QantlyCapability,
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


class QantlyCapabilityInline(admin.TabularInline):
    model = QantlyCapability
    extra = 0


class JobPostingResource(resources.ModelResource):
    company_name = fields.Field(column_name="company_name")
    search_profile_name = fields.Field(column_name="search_profile")

    class Meta:
        model = JobPosting
        fields = (
            "id",
            "title",
            "company_name",
            "company__domain",
            "company__website",
            "company__industry",
            "company__country",
            "search_profile_name",
            "location",
            "source",
            "source_url",
            "source_job_id",
            "description",
            "raw_content",
            "posted_at",
            "discovered_at",
            "matched_signals",
            "requirements",
            "seniority",
            "department",
            "relevance_score",
            "relevance_label",
            "relevance_reason",
            "capability_matches",
            "status",
        )
        export_order = (
            "id",
            "title",
            "company_name",
            "company__domain",
            "company__website",
            "company__industry",
            "company__country",
            "search_profile_name",
            "location",
            "source",
            "source_url",
            "source_job_id",
            "description",
            "raw_content",
            "posted_at",
            "discovered_at",
            "matched_signals",
            "requirements",
            "seniority",
            "department",
            "relevance_score",
            "relevance_label",
            "relevance_reason",
            "capability_matches",
            "status",
        )

    def dehydrate_company_name(self, job):
        return job.company.name

    def dehydrate_search_profile_name(self, job):
        return job.search_profile.name if job.search_profile else ""


@admin.register(SearchProfile)
class SearchProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "freshness_days", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    inlines = (SearchRoleInline, SearchSignalInline, SearchLocationInline, SearchIndustryInline, QantlyCapabilityInline)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "domain", "industry", "country", "updated_at")
    search_fields = ("name", "domain", "industry", "country")
    list_filter = ("industry", "country")


@admin.register(JobPosting)
class JobPostingAdmin(ExportMixin, admin.ModelAdmin):
    resource_classes = (JobPostingResource,)
    list_display = ("title", "company", "relevance_score", "relevance_label", "source", "location", "status", "posted_at", "discovered_at")
    search_fields = ("title", "company__name", "source", "location")
    list_filter = ("status", "relevance_label", "source")
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

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class Company(models.Model):
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, unique=True, null=True, blank=True)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=150, blank=True)
    country = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SearchProfile(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    freshness_days = models.PositiveSmallIntegerField(default=7)
    prospect_threshold = models.PositiveSmallIntegerField(
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum relevance score required for automatic Prospect creation.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SearchRole(models.Model):
    search_profile = models.ForeignKey(SearchProfile, on_delete=models.CASCADE, related_name="roles")
    name = models.CharField(max_length=255)
    weight = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-weight", "name"]
        constraints = [models.UniqueConstraint(fields=["search_profile", "name"], name="unique_profile_role")]

    def __str__(self):
        return f"{self.search_profile}: {self.name}"


class SearchSignal(models.Model):
    class Category(models.TextChoices):
        SKILL = "skill", "Skill"
        METHOD = "method", "Method"
        SOFTWARE = "software", "Software"
        INDUSTRY = "industry", "Industry"
        DOMAIN_SIGNAL = "domain_signal", "Domain signal"
        TECHNOLOGY = "technology", "Technology"
        QUALIFICATION = "qualification", "Qualification"

    search_profile = models.ForeignKey(SearchProfile, on_delete=models.CASCADE, related_name="signals")
    value = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=Category)
    weight = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-weight", "value"]
        constraints = [
            models.UniqueConstraint(fields=["search_profile", "value", "category"], name="unique_profile_signal")
        ]

    def __str__(self):
        return f"{self.search_profile}: {self.value}"


class SearchLocation(models.Model):
    search_profile = models.ForeignKey(SearchProfile, on_delete=models.CASCADE, related_name="locations")
    country = models.CharField(max_length=100)
    region = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["country", "region"]
        constraints = [
            models.UniqueConstraint(fields=["search_profile", "country", "region"], name="unique_profile_location")
        ]

    def __str__(self):
        return ", ".join(part for part in (self.region, self.country) if part)


class SearchIndustry(models.Model):
    search_profile = models.ForeignKey(SearchProfile, on_delete=models.CASCADE, related_name="industries")
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["search_profile", "name"], name="unique_profile_industry")]

    def __str__(self):
        return f"{self.search_profile}: {self.name}"


class QantlyCapability(models.Model):
    class Category(models.TextChoices):
        DESCRIPTIVE_STATISTICS = "descriptive_statistics", "Descriptive statistics"
        HYPOTHESIS_TESTING = "hypothesis_testing", "Hypothesis testing"
        REGRESSION = "regression", "Regression"
        SURVIVAL_ANALYSIS = "survival_analysis", "Survival analysis"
        MULTIVARIATE_ANALYSIS = "multivariate_analysis", "Multivariate analysis"
        MACHINE_LEARNING = "machine_learning", "Machine learning"
        STUDY_DESIGN = "study_design", "Study design"
        POWER_ANALYSIS = "power_analysis", "Power analysis"
        DATA_CLEANING = "data_cleaning", "Data cleaning"
        VISUALIZATION = "visualization", "Visualization"
        REPORTING = "reporting", "Reporting"
        INTERPRETATION = "interpretation", "Interpretation"

    search_profile = models.ForeignKey(SearchProfile, on_delete=models.CASCADE, related_name="capabilities")
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=30, choices=Category.choices)
    keywords = models.JSONField(default=list, blank=True)
    weight = models.PositiveSmallIntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(20)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]
        constraints = [models.UniqueConstraint(fields=["search_profile", "name"], name="unique_profile_capability")]

    def __str__(self):
        return f"{self.search_profile}: {self.name}"


class JobPosting(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        PARSED = "parsed", "Parsed"
        INVALID = "invalid", "Invalid"
        ARCHIVED = "archived", "Archived"

    class RelevanceLabel(models.TextChoices):
        STRONG = "strong", "Strong"
        REVIEW = "review", "Review"
        WEAK = "weak", "Weak"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="job_postings")
    search_profile = models.ForeignKey(
        SearchProfile, on_delete=models.SET_NULL, related_name="job_postings", null=True, blank=True
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=100)
    source_url = models.URLField()
    source_job_id = models.CharField(max_length=255, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    discovered_at = models.DateTimeField(auto_now_add=True)
    raw_content = models.TextField(blank=True)
    requirements = models.JSONField(default=list, blank=True)
    matched_signals = models.JSONField(default=list, blank=True)
    seniority = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=150, blank=True)
    relevance_score = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    relevance_label = models.CharField(max_length=10, choices=RelevanceLabel, default=RelevanceLabel.WEAK)
    relevance_reason = models.TextField(blank=True)
    capability_matches = models.JSONField(default=list, blank=True)
    parsed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status, default=Status.NEW)

    class Meta:
        ordering = ["-discovered_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_job_id"],
                condition=Q(source_job_id__gt=""),
                name="unique_populated_source_job_id",
            )
        ]

    def __str__(self):
        return f"{self.company.name} — {self.title}"


class Prospect(models.Model):
    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class Status(models.TextChoices):
        DISCOVERED = "discovered", "Discovered"
        QUALIFIED = "qualified", "Qualified"
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting approval"
        APPROVED = "approved", "Approved"
        SENT = "sent", "Sent"
        REPLIED = "replied", "Replied"
        DEMO = "demo", "Demo"
        TRIAL = "trial", "Trial"
        CONVERTED = "converted", "Converted"
        LOST = "lost", "Lost"
        CLOSED = "closed", "Closed"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="prospects")
    job_posting = models.OneToOneField(JobPosting, on_delete=models.CASCADE, related_name="prospect")
    fit_score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)], default=0
    )
    fit_reason = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=Priority, default=Priority.MEDIUM)
    status = models.CharField(max_length=25, choices=Status, default=Status.DISCOVERED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fit_score", "-created_at"]

    def __str__(self):
        return f"{self.company.name} ({self.fit_score})"


class Contact(models.Model):
    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "unverified", "Unverified"
        VERIFIED = "verified", "Verified"
        INVALID = "invalid", "Invalid"
        UNKNOWN = "unknown", "Unknown"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    source_url = models.URLField(blank=True)
    verification_status = models.CharField(
        max_length=20, choices=VerificationStatus, default=VerificationStatus.UNVERIFIED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class OutreachEmail(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    class ReplyStatus(models.TextChoices):
        NOT_APPLICABLE = "not_applicable", "Not applicable"
        PENDING = "pending", "Pending"
        REPLIED = "replied", "Replied"
        POSITIVE = "positive", "Positive reply"
        NEGATIVE = "negative", "Negative reply"

    prospect = models.ForeignKey(Prospect, on_delete=models.CASCADE, related_name="outreach_emails")
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, related_name="outreach", null=True, blank=True
    )
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(max_length=25, choices=Status, default=Status.DRAFT)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_outreach",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    reply_status = models.CharField(
        max_length=20, choices=ReplyStatus, default=ReplyStatus.NOT_APPLICABLE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.prospect.company.name}: {self.subject}"


class ProspectEvent(models.Model):
    class EventType(models.TextChoices):
        DISCOVERED = "discovered", "Discovered"
        QUALIFIED = "qualified", "Qualified"
        STATUS_CHANGED = "status_changed", "Status changed"
        OUTREACH_DRAFTED = "outreach_drafted", "Outreach drafted"
        OUTREACH_APPROVED = "outreach_approved", "Outreach approved"
        OUTREACH_REJECTED = "outreach_rejected", "Outreach rejected"
        OUTREACH_SENT = "outreach_sent", "Outreach sent"
        REPLY_RECEIVED = "reply_received", "Reply received"
        NOTE = "note", "Note"

    prospect = models.ForeignKey(Prospect, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=30, choices=EventType)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.prospect}: {self.get_event_type_display()}"

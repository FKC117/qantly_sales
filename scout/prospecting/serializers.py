from rest_framework import serializers

from .models import Company, Contact, JobPosting, Outreach, Prospect, ProspectActivity


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class JobPostingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosting
        fields = "__all__"
        read_only_fields = ("id", "discovered_at")


class ProspectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prospect
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        company = attrs.get("company", getattr(self.instance, "company", None))
        job_posting = attrs.get("job_posting", getattr(self.instance, "job_posting", None))
        if company and job_posting and job_posting.company_id != company.id:
            raise serializers.ValidationError({"job_posting": "The job posting must belong to this company."})
        return attrs


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class OutreachSerializer(serializers.ModelSerializer):
    class Meta:
        model = Outreach
        fields = "__all__"
        read_only_fields = (
            "id",
            "status",
            "approved_by",
            "approved_at",
            "sent_at",
            "reply_status",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        prospect = attrs.get("prospect", getattr(self.instance, "prospect", None))
        contact = attrs.get("contact", getattr(self.instance, "contact", None))
        if prospect and contact and contact.company_id != prospect.company_id:
            raise serializers.ValidationError({"contact": "The contact must belong to the prospect company."})
        return attrs


class ProspectActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProspectActivity
        fields = "__all__"
        read_only_fields = fields

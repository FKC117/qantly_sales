from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import Company, Contact, JobPosting, Outreach, Prospect, ProspectActivity
from .serializers import (
    CompanySerializer,
    ContactSerializer,
    JobPostingSerializer,
    OutreachSerializer,
    ProspectActivitySerializer,
    ProspectSerializer,
)
from .services import approve_outreach, log_activity, reject_outreach, submit_outreach_for_approval


@api_view(["GET"])
def health_check(request):
    """Confirm that the prospecting API is installed and reachable."""
    return Response({"app": "prospecting", "status": "ok"})


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]


class JobPostingViewSet(viewsets.ModelViewSet):
    queryset = JobPosting.objects.select_related("company").all()
    serializer_class = JobPostingSerializer
    permission_classes = [IsAuthenticated]


class ProspectViewSet(viewsets.ModelViewSet):
    queryset = Prospect.objects.select_related("company", "job_posting").all()
    serializer_class = ProspectSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        prospect = serializer.save()
        log_activity(prospect, ProspectActivity.EventType.DISCOVERED)

    def perform_update(self, serializer):
        previous_status = self.get_object().status
        prospect = serializer.save()
        if prospect.status != previous_status:
            log_activity(
                prospect,
                ProspectActivity.EventType.STATUS_CHANGED,
                {"from": previous_status, "to": prospect.status},
            )


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.select_related("company").all()
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]


class OutreachViewSet(viewsets.ModelViewSet):
    queryset = Outreach.objects.select_related("prospect__company", "contact", "approved_by").all()
    serializer_class = OutreachSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in {"approve", "reject"}:
            return [IsAdminUser()]
        return super().get_permissions()

    def update(self, request, *args, **kwargs):
        outreach = self.get_object()
        if outreach.status == Outreach.Status.SENT:
            return Response({"detail": "Sent outreach cannot be edited."}, status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, **kwargs)

    def _transition(self, request, transition):
        try:
            outreach = transition(self.get_object())
        except DjangoValidationError as error:
            return Response({"detail": error.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(outreach).data)

    @action(detail=True, methods=["post"], url_path="submit-for-approval")
    def submit_for_approval(self, request, pk=None):
        return self._transition(request, submit_outreach_for_approval)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._transition(request, lambda outreach: approve_outreach(outreach, request.user))

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._transition(request, lambda outreach: reject_outreach(outreach, request.user))


class ProspectActivityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProspectActivity.objects.select_related("prospect__company").all()
    serializer_class = ProspectActivitySerializer
    permission_classes = [IsAuthenticated]

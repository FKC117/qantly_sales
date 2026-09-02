import json

from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from django_celery_results.models import TaskResult
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

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
from .serializers import (
    CompanySerializer,
    ContactSerializer,
    JobPostingSerializer,
    OutreachEmailSerializer,
    ProspectEventSerializer,
    QantlyCapabilitySerializer,
    ProspectSerializer,
    SearchIndustrySerializer,
    SearchLocationSerializer,
    SearchProfileSerializer,
    SearchRoleSerializer,
    SearchSignalSerializer,
)
from .services import approve_outreach, log_activity, reject_outreach, submit_outreach_for_approval
from .research.assessment import assess_prospect
from .research.services import research_prospect
from .outreach.generator import generate_outreach_email


@require_GET
@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({"detail": "CSRF cookie set."})


@require_POST
@csrf_protect
def session_login(request):
    try:
        credentials = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON."}, status=400)
    user = authenticate(request, username=credentials.get("username", ""), password=credentials.get("password", ""))
    if user is None:
        return JsonResponse({"detail": "Invalid username or password."}, status=400)
    login(request, user)
    return JsonResponse({"username": user.get_username(), "is_staff": user.is_staff})


@require_POST
@csrf_protect
def session_logout(request):
    logout(request)
    return JsonResponse({"detail": "Logged out."})


@require_GET
def session_user(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Not authenticated."}, status=401)
    return JsonResponse({"username": request.user.get_username(), "is_staff": request.user.is_staff})


@api_view(["GET"])
def health_check(request):
    """Confirm that the prospecting API is installed and reachable."""
    return Response({"app": "prospecting", "status": "ok"})


@api_view(["GET"])
@permission_classes([IsAdminUser])
def discovery_status(request, task_id):
    """Expose the result of a user-triggered discovery task to the dashboard."""
    task = TaskResult.objects.filter(task_id=task_id).first()
    if task is None:
        return Response({"task_id": task_id, "status": "PENDING", "result": None})
    result = task.result
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            pass
    return Response({"task_id": task_id, "status": task.status, "result": result})


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]


class SearchProfileViewSet(viewsets.ModelViewSet):
    queryset = SearchProfile.objects.all()
    serializer_class = SearchProfileSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def activate(self, request, pk=None):
        profile = self.get_object()
        profile.is_active = True
        profile.save(update_fields=["is_active", "updated_at"])
        return Response(self.get_serializer(profile).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def deactivate(self, request, pk=None):
        profile = self.get_object()
        profile.is_active = False
        profile.save(update_fields=["is_active", "updated_at"])
        return Response(self.get_serializer(profile).data)

    @action(detail=True, methods=["post"], url_path="run-discovery", permission_classes=[IsAdminUser])
    def run_discovery(self, request, pk=None):
        """Queue one discovery run for this active profile."""
        from .tasks import discover_jobs_task

        profile = self.get_object()
        if not profile.is_active:
            return Response(
                {"detail": "Activate this search profile before running discovery."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task = discover_jobs_task.delay(profile.id)
        return Response(
            {"task_id": str(task.id), "profile": profile.name},
            status=status.HTTP_202_ACCEPTED,
        )


class SearchRoleViewSet(viewsets.ModelViewSet):
    queryset = SearchRole.objects.select_related("search_profile").all()
    serializer_class = SearchRoleSerializer
    permission_classes = [IsAuthenticated]


class SearchSignalViewSet(viewsets.ModelViewSet):
    queryset = SearchSignal.objects.select_related("search_profile").all()
    serializer_class = SearchSignalSerializer
    permission_classes = [IsAuthenticated]


class SearchLocationViewSet(viewsets.ModelViewSet):
    queryset = SearchLocation.objects.select_related("search_profile").all()
    serializer_class = SearchLocationSerializer
    permission_classes = [IsAuthenticated]


class SearchIndustryViewSet(viewsets.ModelViewSet):
    queryset = SearchIndustry.objects.select_related("search_profile").all()
    serializer_class = SearchIndustrySerializer
    permission_classes = [IsAuthenticated]


class QantlyCapabilityViewSet(viewsets.ModelViewSet):
    queryset = QantlyCapability.objects.select_related("search_profile").all()
    serializer_class = QantlyCapabilitySerializer
    permission_classes = [IsAuthenticated]


class JobPostingViewSet(viewsets.ModelViewSet):
    queryset = JobPosting.objects.select_related("company").all()
    serializer_class = JobPostingSerializer
    permission_classes = [IsAuthenticated]


class ProspectViewSet(viewsets.ModelViewSet):
    queryset = Prospect.objects.select_related("company", "job_posting", "research", "assessment").all()
    serializer_class = ProspectSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        prospect = serializer.save()
        log_activity(prospect, ProspectEvent.EventType.DISCOVERED)

    def perform_update(self, serializer):
        previous_status = self.get_object().status
        prospect = serializer.save()
        if prospect.status != previous_status:
            log_activity(
                prospect,
                ProspectEvent.EventType.STATUS_CHANGED,
                {"from": previous_status, "to": prospect.status},
            )

    @action(detail=True, methods=["post"])
    def research(self, request, pk=None):
        research = research_prospect(self.get_object(), force=bool(request.data.get("force", False)))
        return Response({"research": research.id})

    @action(detail=True, methods=["post"])
    def assess(self, request, pk=None):
        assessment = assess_prospect(self.get_object(), force_research=bool(request.data.get("force", False)))
        return Response({"assessment": assessment.id, "classification": assessment.classification})

    @action(detail=True, methods=["post"], url_path="qualify")
    def qualify(self, request, pk=None):
        assessment = assess_prospect(self.get_object(), force_research=bool(request.data.get("force", False)))
        return Response({"assessment": assessment.id, "classification": assessment.classification})

    @action(detail=True, methods=["post"], url_path="generate-outreach")
    def generate_outreach(self, request, pk=None):
        prospect = self.get_object()
        if not hasattr(prospect, "assessment"):
            return Response({"detail": "Assess the prospect before generating outreach."}, status=status.HTTP_400_BAD_REQUEST)
        outreach = generate_outreach_email(prospect)
        return Response(OutreachEmailSerializer(outreach).data, status=status.HTTP_201_CREATED)


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.select_related("company").all()
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]


class OutreachEmailViewSet(viewsets.ModelViewSet):
    queryset = OutreachEmail.objects.select_related("prospect__company", "contact", "approved_by").all()
    serializer_class = OutreachEmailSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in {"approve", "reject", "queue_send"}:
            return [IsAdminUser()]
        return super().get_permissions()

    def update(self, request, *args, **kwargs):
        outreach = self.get_object()
        if outreach.status == OutreachEmail.Status.SENT:
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

    @action(detail=True, methods=["post"], url_path="queue-send")
    def queue_send(self, request, pk=None):
        """Queue SMTP delivery for an approved email; the worker enforces approval again."""
        outreach = self.get_object()
        if outreach.status != OutreachEmail.Status.APPROVED:
            return Response({"detail": "Only approved outreach can be queued for sending."}, status=status.HTTP_400_BAD_REQUEST)
        from .tasks import send_approved_outreach_task

        task = send_approved_outreach_task.delay(outreach.id)
        return Response({"outreach": outreach.id, "task_id": str(task.id)}, status=status.HTTP_202_ACCEPTED)


class ProspectEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProspectEvent.objects.select_related("prospect__company").all()
    serializer_class = ProspectEventSerializer
    permission_classes = [IsAuthenticated]

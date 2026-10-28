import ast
import json

from django.db.models import Q
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.api.schema import job_detail_schema, job_list_schema
from apps.jobs.api.serializers import JobSerializer
from apps.jobs.models import Job, JobSource
from apps.jobs.services.ingestion import JobIngestionService
from apps.matching.services.match_job_to_profile import match_job_to_profile
from apps.users.models import CareerProfile


@job_list_schema
class JobListCreateAPIView(ListCreateAPIView):
    serializer_class = JobSerializer

    def get_queryset(self):
        queryset = Job.objects.prefetch_related("skills").all()

        include_expired = str(self.request.query_params.get("include_expired", "false")).lower() == "true"
        if not include_expired:
            queryset = queryset.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))

        search = self.request.query_params.get("search", "").strip()
        title = self.request.query_params.get("title", "").strip()
        company = self.request.query_params.get("company", "").strip()
        location = self.request.query_params.get("location", "").strip()
        work_type = self.request.query_params.get("work_type")
        employment_type = self.request.query_params.get("employment_type")
        skills = self.request.query_params.getlist("skills")
        ordering = self.request.query_params.get("ordering", "-created_at")

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(company_name__icontains=search)
                | Q(description__icontains=search)
                | Q(location__icontains=search)
                | Q(skills__name__icontains=search)
            ).distinct()

        if title:
            queryset = queryset.filter(title__icontains=title)

        if company:
            queryset = queryset.filter(company_name__icontains=company)

        if location:
            queryset = queryset.filter(location__icontains=location)

        if work_type:
            queryset = queryset.filter(work_type=work_type)

        if employment_type:
            queryset = queryset.filter(employment_type=employment_type)

        if skills:
            skill_names = []
            for value in skills:
                skill_names.extend(part.strip() for part in value.split(",") if part.strip())
            if skill_names:
                queryset = queryset.filter(skills__name__in=skill_names).distinct()

        allowed_ordering = {
            "title",
            "company_name",
            "location",
            "work_type",
            "employment_type",
            "posted_at",
            "expires_at",
            "created_at",
            "updated_at",
            "-title",
            "-company_name",
            "-location",
            "-work_type",
            "-employment_type",
            "-posted_at",
            "-expires_at",
            "-created_at",
            "-updated_at",
        }

        if ordering in allowed_ordering:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        return queryset


@job_detail_schema
class JobDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Job.objects.prefetch_related("skills").all()
    serializer_class = JobSerializer


class JobMatchAPIView(APIView):
    @extend_schema(
        summary="Match a job to the current user's profile",
        description="Return rule-based matching scores and component explanations for a job.",
        responses=OpenApiTypes.OBJECT,
        tags=["Jobs"],
    )
    def get(self, request, pk, *args, **kwargs):
        try:
            job = Job.objects.prefetch_related("skills").get(pk=pk)
        except Job.DoesNotExist:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        profile = CareerProfile.objects.filter(user=request.user).first()
        if profile is None:
            return Response({"detail": "No career profile found for this user."}, status=status.HTTP_404_NOT_FOUND)

        result = match_job_to_profile(profile, job)
        return Response(result, status=status.HTTP_200_OK)


class JobIngestAPIView(APIView):
    def _coerce_jobs_payload(self, payload):
        if payload is None:
            return []
        if isinstance(payload, list):
            return payload
        if isinstance(payload, tuple):
            return list(payload)
        if isinstance(payload, dict):
            if "jobs" in payload:
                return self._coerce_jobs_payload(payload["jobs"])
            return [payload]
        if isinstance(payload, str):
            stripped = payload.strip()
            if not stripped:
                return []
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                try:
                    parsed = ast.literal_eval(stripped)
                except (ValueError, SyntaxError):
                    return [payload]
            return self._coerce_jobs_payload(parsed)
        if hasattr(payload, "getlist"):
            raw_values = payload.getlist("jobs")
            if raw_values:
                if len(raw_values) == 1:
                    return self._coerce_jobs_payload(raw_values[0])
                return [self._coerce_jobs_payload(value) for value in raw_values]
        return [payload] if isinstance(payload, dict) else payload

    def _extract_request_data(self, request):
        payload = getattr(request, "data", None)
        if payload is not None:
            if hasattr(payload, "get"):
                source_value = payload.get("source")
                jobs_value = payload.get("jobs")
                if source_value is not None or jobs_value is not None:
                    return source_value, jobs_value

        post_data = getattr(request, "POST", None)
        if post_data is not None and hasattr(post_data, "get"):
            return post_data.get("source"), post_data.get("jobs")

        raw_body = getattr(request, "body", b"")
        if raw_body:
            try:
                decoded = raw_body.decode("utf-8")
            except (UnicodeDecodeError, AttributeError):
                decoded = str(raw_body)
            try:
                body_data = json.loads(decoded)
            except (TypeError, ValueError):
                body_data = {}
            if isinstance(body_data, dict):
                return body_data.get("source"), body_data.get("jobs")

        return None, []

    @extend_schema(
        summary="Ingest jobs",
        description="Ingest one or more job records for the supplied source and return ingestion counts.",
        request=OpenApiTypes.OBJECT,
        responses=OpenApiTypes.OBJECT,
        tags=["Jobs"],
    )
    def post(self, request, *args, **kwargs):
        source_slug, jobs_value = self._extract_request_data(request)
        source_slug = (source_slug or "linkedin").strip() or "linkedin"
        jobs_payload = self._coerce_jobs_payload(jobs_value)

        if not isinstance(jobs_payload, list):
            return Response({"detail": "jobs must be a list."}, status=status.HTTP_400_BAD_REQUEST)

        source, _ = JobSource.objects.get_or_create(
            slug=source_slug,
            defaults={"name": source_slug.title(), "base_url": f"https://{source_slug}.example.com"},
        )

        result = JobIngestionService(source=source).ingest(jobs_payload)
        return Response(result, status=status.HTTP_200_OK)

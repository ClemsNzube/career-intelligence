from django.db.models import Q
from django.utils import timezone
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from apps.jobs.api.schema import job_detail_schema, job_list_schema
from apps.jobs.api.serializers import JobSerializer
from apps.jobs.models import Job


@job_list_schema
class JobListCreateAPIView(ListCreateAPIView):
    serializer_class = JobSerializer

    def get_queryset(self):
        queryset = Job.objects.prefetch_related("skills").all()

        include_expired = str(self.request.query_params.get("include_expired", "false")).lower() == "true"
        if not include_expired:
            queryset = queryset.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))

        search = self.request.query_params.get("search", "").strip()
        work_type = self.request.query_params.get("work_type")
        employment_type = self.request.query_params.get("employment_type")
        skills = self.request.query_params.getlist("skills")
        ordering = self.request.query_params.get("ordering", "-created_at")

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(company_name__icontains=search)
                | Q(description__icontains=search)
                | Q(skills__name__icontains=search)
            ).distinct()

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

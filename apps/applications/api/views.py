from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.applications.api.serializers import (
    ApplicationDashboardSerializer,
    ApplicationStatsSerializer,
    JobApplicationSerializer,
)
from apps.applications.models import JobApplication


ACTIVE_FOLLOW_UP_STATUSES = (
    JobApplication.Status.SAVED,
    JobApplication.Status.APPLIED,
    JobApplication.Status.INTERVIEW,
    JobApplication.Status.OFFER,
)


def _application_stats(user):
    return JobApplication.objects.filter(user=user).aggregate(
        total=Count("id"),
        saved=Count("id", filter=Q(status=JobApplication.Status.SAVED)),
        applied=Count("id", filter=Q(status=JobApplication.Status.APPLIED)),
        interview=Count("id", filter=Q(status=JobApplication.Status.INTERVIEW)),
        offer=Count("id", filter=Q(status=JobApplication.Status.OFFER)),
        rejected=Count("id", filter=Q(status=JobApplication.Status.REJECTED)),
        withdrawn=Count("id", filter=Q(status=JobApplication.Status.WITHDRAWN)),
    )


def _user_applications(user):
    return (
        JobApplication.objects.filter(user=user)
        .select_related("job")
        .prefetch_related("job__skills")
    )


class JobApplicationListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            JobApplication.objects.filter(user=self.request.user)
            .select_related("job")
            .prefetch_related("job__skills")
            .order_by("-updated_at", "-pk")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class JobApplicationDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            JobApplication.objects.filter(user=self.request.user)
            .select_related("job")
            .prefetch_related("job__skills")
        )


class ApplicationStatsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get application statistics",
        description="Return status counts for the authenticated user's tracked jobs.",
        responses=ApplicationStatsSerializer,
        tags=["Applications"],
    )
    def get(self, request):
        return Response(_application_stats(request.user))


class ApplicationFollowUpsView(ListAPIView):
    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            JobApplication.objects.filter(
                user=self.request.user,
                follow_up_at__date__lte=timezone.localdate(),
                status__in=ACTIVE_FOLLOW_UP_STATUSES,
            )
            .select_related("job")
            .prefetch_related("job__skills")
            .order_by("follow_up_at", "pk")
        )


class ApplicationDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get application dashboard",
        description=(
            "Return status counts, up to five soonest scheduled follow-ups, "
            "and the ten most recently updated applications for the authenticated user."
        ),
        responses=ApplicationDashboardSerializer,
        tags=["Applications"],
    )
    def get(self, request):
        applications = _user_applications(request.user)
        follow_ups = applications.filter(
            follow_up_at__isnull=False,
            status__in=ACTIVE_FOLLOW_UP_STATUSES,
        ).order_by("follow_up_at", "pk")[:5]
        recent_applications = applications.order_by("-updated_at", "-pk")[:10]
        serializer_context = {"request": request}

        return Response(
            {
                "stats": _application_stats(request.user),
                "follow_ups": JobApplicationSerializer(
                    follow_ups,
                    many=True,
                    context=serializer_context,
                ).data,
                "applications": JobApplicationSerializer(
                    recent_applications,
                    many=True,
                    context=serializer_context,
                ).data,
            }
        )

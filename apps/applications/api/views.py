from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.applications.api.serializers import JobApplicationSerializer
from apps.applications.models import JobApplication


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

    def get(self, request):
        counts = JobApplication.objects.filter(user=request.user).aggregate(
            total=Count("id"),
            saved=Count("id", filter=Q(status=JobApplication.Status.SAVED)),
            applied=Count("id", filter=Q(status=JobApplication.Status.APPLIED)),
            interview=Count("id", filter=Q(status=JobApplication.Status.INTERVIEW)),
            offer=Count("id", filter=Q(status=JobApplication.Status.OFFER)),
            rejected=Count("id", filter=Q(status=JobApplication.Status.REJECTED)),
            withdrawn=Count("id", filter=Q(status=JobApplication.Status.WITHDRAWN)),
        )
        return Response(counts)


class ApplicationFollowUpsView(ListAPIView):
    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            JobApplication.objects.filter(
                user=self.request.user,
                follow_up_at__date__lte=timezone.localdate(),
                status__in=[
                    JobApplication.Status.SAVED,
                    JobApplication.Status.APPLIED,
                    JobApplication.Status.INTERVIEW,
                    JobApplication.Status.OFFER,
                ],
            )
            .select_related("job")
            .prefetch_related("job__skills")
            .order_by("follow_up_at", "pk")
        )

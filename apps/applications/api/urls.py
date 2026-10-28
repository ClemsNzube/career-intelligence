from django.urls import path

from apps.applications.api.views import (
    ApplicationFollowUpsView,
    ApplicationStatsView,
    JobApplicationDetailAPIView,
    JobApplicationListCreateAPIView,
)

urlpatterns = [
    path("", JobApplicationListCreateAPIView.as_view(), name="application-list"),
    path("stats/", ApplicationStatsView.as_view(), name="application-stats"),
    path(
        "follow-ups/",
        ApplicationFollowUpsView.as_view(),
        name="application-follow-ups",
    ),
    path(
        "<int:pk>/",
        JobApplicationDetailAPIView.as_view(),
        name="application-detail",
    ),
]

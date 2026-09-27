from django.urls import path

from .views import JobDetailAPIView, JobIngestAPIView, JobListCreateAPIView, JobMatchAPIView

urlpatterns = [
    path("", JobListCreateAPIView.as_view(), name="job-list"),
    path("ingest/", JobIngestAPIView.as_view(), name="job-ingest"),
    path("<int:pk>/match/", JobMatchAPIView.as_view(), name="job-match"),
    path("<int:pk>/", JobDetailAPIView.as_view(), name="job-detail"),
]
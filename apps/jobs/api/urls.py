from django.urls import path
from .views import JobListAPIView

urlpatterns = [
    path("", JobListAPIView.as_view(), name="job-list"),
]
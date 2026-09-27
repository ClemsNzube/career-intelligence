from django.urls import path

from apps.recommendations.api.views import JobRecommendationsAPIView

urlpatterns = [
    path("", JobRecommendationsAPIView.as_view(), name="job-recommendations"),
]
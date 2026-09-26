from django.urls import path

from .health import health_check
from .views import (
    CareerPreferencesDetailAPIView,
    CareerPreferencesListCreateAPIView,
    CareerProfileDetailAPIView,
    CareerProfileListCreateAPIView,
    CertificationDetailAPIView,
    CertificationListCreateAPIView,
    EducationDetailAPIView,
    EducationListCreateAPIView,
    ExperienceDetailAPIView,
    ExperienceListCreateAPIView,
    ProjectDetailAPIView,
    ProjectListCreateAPIView,
)

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('profiles/', CareerProfileListCreateAPIView.as_view(), name='profile-list'),
    path('profiles/<int:pk>/', CareerProfileDetailAPIView.as_view(), name='profile-detail'),
    path('preferences/', CareerPreferencesListCreateAPIView.as_view(), name='career-preferences-list'),
    path('preferences/<int:pk>/', CareerPreferencesDetailAPIView.as_view(), name='career-preferences-detail'),
    path('education/', EducationListCreateAPIView.as_view(), name='education-list'),
    path('education/<int:pk>/', EducationDetailAPIView.as_view(), name='education-detail'),
    path('experience/', ExperienceListCreateAPIView.as_view(), name='experience-list'),
    path('experience/<int:pk>/', ExperienceDetailAPIView.as_view(), name='experience-detail'),
    path('certifications/', CertificationListCreateAPIView.as_view(), name='certification-list'),
    path('certifications/<int:pk>/', CertificationDetailAPIView.as_view(), name='certification-detail'),
    path('projects/', ProjectListCreateAPIView.as_view(), name='project-list'),
    path('projects/<int:pk>/', ProjectDetailAPIView.as_view(), name='project-detail'),
]


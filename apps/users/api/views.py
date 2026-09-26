from rest_framework import generics

from apps.users.api.serializers import (
    CareerPreferencesSerializer,
    CareerProfileSerializer,
    CertificationSerializer,
    EducationSerializer,
    ExperienceSerializer,
    ProjectSerializer,
)
from apps.users.models import (
    CareerPreferences,
    CareerProfile,
    Certification,
    Education,
    Experience,
    Project,
)


class CareerProfileListCreateAPIView(generics.ListCreateAPIView):
    queryset = CareerProfile.objects.all()
    serializer_class = CareerProfileSerializer


class CareerProfileDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CareerProfile.objects.all()
    serializer_class = CareerProfileSerializer


class CareerPreferencesListCreateAPIView(generics.ListCreateAPIView):
    queryset = CareerPreferences.objects.all()
    serializer_class = CareerPreferencesSerializer


class CareerPreferencesDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CareerPreferences.objects.all()
    serializer_class = CareerPreferencesSerializer


class EducationListCreateAPIView(generics.ListCreateAPIView):
    queryset = Education.objects.all()
    serializer_class = EducationSerializer


class EducationDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Education.objects.all()
    serializer_class = EducationSerializer


class ExperienceListCreateAPIView(generics.ListCreateAPIView):
    queryset = Experience.objects.all()
    serializer_class = ExperienceSerializer


class ExperienceDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Experience.objects.all()
    serializer_class = ExperienceSerializer


class CertificationListCreateAPIView(generics.ListCreateAPIView):
    queryset = Certification.objects.all()
    serializer_class = CertificationSerializer


class CertificationDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Certification.objects.all()
    serializer_class = CertificationSerializer


class ProjectListCreateAPIView(generics.ListCreateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer


class ProjectDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

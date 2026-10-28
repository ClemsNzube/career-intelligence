from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.intelligence.normalization.profile_skills import classify_profile_skills
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


class CareerProfileSkillSuggestionsAPIView(APIView):
    @extend_schema(
        summary="Suggest skills from profile evidence",
        description="Return uncertain skill mentions for review without linking them automatically.",
        responses=OpenApiTypes.OBJECT,
        tags=["Profiles"],
    )
    def get(self, request, pk, *args, **kwargs):
        profile = get_object_or_404(
            CareerProfile.objects.prefetch_related(
                "skills",
                "work_experiences__skills_used",
                "projects__skills_used",
            ),
            pk=pk,
        )
        _, suggestions = classify_profile_skills(profile)
        return Response(
            {
                "profile": profile.pk,
                "suggestions": [
                    {"id": skill.pk, "name": skill.name, "reason": reason}
                    for skill, reason in suggestions
                ],
            }
        )


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

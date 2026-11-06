from mimetypes import guess_type

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.skills.models import Skill
from apps.users.api.cv_serializers import CVDocumentSerializer
from apps.users.models import CVDocument, CareerProfile


class CVDocumentListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = CVDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CVDocument.objects.filter(user=self.request.user)


class CVDocumentDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CVDocumentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return CVDocument.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        instance.delete()


class CVDocumentDownloadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Download original CV",
        description="Download the original PDF or DOCX uploaded by the authenticated user.",
        responses={(200, "application/octet-stream"): OpenApiTypes.BINARY},
        tags=["Candidate CVs"],
    )
    def get(self, request, pk):
        document = get_object_or_404(CVDocument, pk=pk, user=request.user)
        content_type, _ = guess_type(document.original_filename)
        return FileResponse(
            document.file.open("rb"),
            as_attachment=True,
            filename=document.original_filename,
            content_type=content_type or "application/octet-stream",
        )


class CVDocumentApproveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Approve reviewed CV extraction",
        description="Apply confirmed CV skills and summary to the user's career profile.",
        request=None,
        responses=CVDocumentSerializer,
        tags=["Candidate CVs"],
    )
    def post(self, request, pk):
        document = get_object_or_404(CVDocument, pk=pk, user=request.user)
        if document.status != CVDocument.Status.REVIEW:
            return Response(
                {"detail": "Only CVs awaiting review can be approved."},
                status=status.HTTP_409_CONFLICT,
            )

        extracted_data = document.extracted_data
        skill_names = extracted_data.get("skills", [])
        if not isinstance(skill_names, list) or not all(
            isinstance(name, str) for name in skill_names
        ):
            return Response(
                {"extracted_data": {"skills": "Skills must be a list of names."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            profile, _ = CareerProfile.objects.get_or_create(user=request.user)
            known_skills = []
            for name in skill_names:
                skill = Skill.objects.filter(name__iexact=name.strip()).first()
                if skill is not None and skill not in known_skills:
                    known_skills.append(skill)
            if known_skills:
                profile.skills.add(*known_skills)
            summary = extracted_data.get("summary", "")
            if isinstance(summary, str) and summary.strip():
                profile.bio = summary.strip()
                profile.save(update_fields=["bio", "updated_at"])

            document.status = CVDocument.Status.APPROVED
            document.reviewed_at = timezone.now()
            document.save(update_fields=["status", "reviewed_at", "updated_at"])
        return Response(CVDocumentSerializer(document).data)

from rest_framework import serializers

from apps.skills.models import Skill
from apps.users.models import (
    CareerPreferences,
    CareerProfile,
    Certification,
    Education,
    Experience,
    Project,
)


class CareerProfileSerializer(serializers.ModelSerializer):
    preferred_locations = serializers.JSONField(required=False, allow_null=True, default=list)

    class Meta:
        model = CareerProfile
        fields = [
            "id",
            "user",
            "related_name",
            "bio",
            "year_of_experience",
            "preferred_locations",
            "preferred_work_type",
            "skills",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_preferred_locations(self, value):
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return value


class CareerPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerPreferences
        fields = [
            "id",
            "career_profile",
            "target_job_titles",
            "target_industries",
            "preferred_locations",
            "preferred_work_types",
            "min_years_of_experience",
            "max_years_of_experience",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = [
            "id",
            "career_profile",
            "institution",
            "degree",
            "field_of_study",
            "start_date",
            "end_date",
            "currently_studying",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ExperienceSerializer(serializers.ModelSerializer):
    skills_used = serializers.PrimaryKeyRelatedField(many=True, queryset=Skill.objects.all(), required=False)

    class Meta:
        model = Experience
        fields = [
            "id",
            "career_profile",
            "job_title",
            "company",
            "employment_type",
            "location",
            "start_date",
            "end_date",
            "currently_working",
            "description",
            "skills_used",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certification
        fields = [
            "id",
            "career_profile",
            "name",
            "issuing_organization",
            "issue_date",
            "expiration_date",
            "credential_id",
            "credential_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProjectSerializer(serializers.ModelSerializer):
    skills_used = serializers.PrimaryKeyRelatedField(many=True, queryset=Skill.objects.all(), required=False)

    class Meta:
        model = Project
        fields = [
            "id",
            "career_profile",
            "name",
            "description",
            "role",
            "project_url",
            "repository_url",
            "start_date",
            "end_date",
            "skills_used",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

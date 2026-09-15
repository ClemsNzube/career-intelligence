from rest_framework import serializers
from apps.jobs.models import Job

class JobSerializer(serializers.ModelSerializer):
    skills = serializers.StringRelatedField(many=True)
    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "company_name",
            "location",
            "work_type",
            "employment_type",
            "application_url",
            "source",
            "posted_at",
            "expires_at",
            "skills",
            "created_at",
            "updated_at",
        ]


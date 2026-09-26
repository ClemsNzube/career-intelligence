from django.utils.text import slugify
from rest_framework import serializers

from apps.jobs.models import Job
from apps.skills.models import Skill


class JobSerializer(serializers.ModelSerializer):
    skills = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "company_name",
            "description",
            "location",
            "work_type",
            "employment_type",
            "application_url",
            "source",
            "external_id",
            "posted_at",
            "expires_at",
            "skills",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        required_fields = [
            "title",
            "company_name",
            "description",
            "location",
            "work_type",
            "employment_type",
            "application_url",
        ]

        for field_name in required_fields:
            value = attrs.get(field_name)
            if isinstance(value, str) and not value.strip():
                raise serializers.ValidationError({field_name: "This field may not be blank."})

        work_type_choices = dict(Job.WORK_TYPE_CHOICES)
        employment_type_choices = dict(Job.EMPLOYMENT_TYPE_CHOICES)

        if attrs.get("work_type") and attrs["work_type"] not in work_type_choices:
            raise serializers.ValidationError({"work_type": "Invalid work type."})

        if attrs.get("employment_type") and attrs["employment_type"] not in employment_type_choices:
            raise serializers.ValidationError({"employment_type": "Invalid employment type."})

        return attrs

    def _sync_skills(self, job, skill_names):
        skill_objects = []

        for raw_name in skill_names or []:
            name = (raw_name or "").strip()
            if not name:
                continue

            skill = Skill.objects.filter(name__iexact=name).first()
            if not skill:
                skill = Skill.objects.create(name=name, slug=slugify(name)[:120])
            skill_objects.append(skill)

        job.skills.set(skill_objects)

    def create(self, validated_data):
        skill_names = validated_data.pop("skills", [])
        job = Job.objects.create(**validated_data)
        self._sync_skills(job, skill_names)
        return job

    def update(self, instance, validated_data):
        skill_names = validated_data.pop("skills", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if skill_names is not None:
            self._sync_skills(instance, skill_names)

        return instance


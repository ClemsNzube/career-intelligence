from django.utils.text import slugify
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.jobs.models import Job
from apps.skills.models import Skill


@extend_schema_field({"type": "array", "items": {"type": "string"}})
class SkillNamesField(serializers.Field):
    def to_representation(self, value):
        if value is None:
            return []
        if hasattr(value, "all"):
            return [skill.name for skill in value.all()]
        if isinstance(value, (list, tuple)):
            return [str(item) for item in value]
        return [str(value)]

    def to_internal_value(self, data):
        if data is None:
            return []
        if isinstance(data, str):
            data = [data]
        if not isinstance(data, (list, tuple)):
            raise serializers.ValidationError("Skills must be a list of skill names.")

        cleaned = []
        for item in data:
            name = str(item).strip()
            if name:
                cleaned.append(name)
        return cleaned


class JobSerializer(serializers.ModelSerializer):
    skills = SkillNamesField(required=False, allow_null=True)

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
            "is_expired",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "is_expired"]

    def validate(self, attrs):
        for field_name in [
            "title",
            "company_name",
            "description",
            "location",
            "work_type",
            "employment_type",
            "application_url",
        ]:
            value = attrs.get(field_name)
            if isinstance(value, str) and not value.strip():
                raise serializers.ValidationError({field_name: "This field may not be blank."})

        for field_name in ["title", "company_name", "location", "source", "external_id", "application_url"]:
            value = attrs.get(field_name)
            if isinstance(value, str):
                attrs[field_name] = value.strip()

        if attrs.get("title"):
            attrs["title"] = Job.normalize_title(attrs["title"])

        if attrs.get("description"):
            attrs["description"] = Job.clean_description(attrs["description"])

        work_type_choices = dict(Job.WORK_TYPE_CHOICES)
        employment_type_choices = dict(Job.EMPLOYMENT_TYPE_CHOICES)

        if attrs.get("work_type") and attrs["work_type"] not in work_type_choices:
            raise serializers.ValidationError({"work_type": "Invalid work type."})

        if attrs.get("employment_type") and attrs["employment_type"] not in employment_type_choices:
            raise serializers.ValidationError({"employment_type": "Invalid employment type."})

        external_id = (attrs.get("external_id") or "").strip()
        if external_id:
            queryset = Job.objects.filter(external_id=external_id)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError({"external_id": "A job with this external identifier already exists."})

        title = (attrs.get("title") or "").strip()
        company_name = (attrs.get("company_name") or "").strip()
        application_url = (attrs.get("application_url") or "").strip()
        source = (attrs.get("source") or "").strip()

        if title and company_name and application_url:
            duplicate_exists = Job.objects.filter(
                title__iexact=title,
                company_name__iexact=company_name,
                application_url__iexact=application_url,
            )
            if self.instance:
                duplicate_exists = duplicate_exists.exclude(pk=self.instance.pk)
            if duplicate_exists.exists():
                raise serializers.ValidationError({"non_field_errors": ["A duplicate job already exists for this title, company, and application URL."]})

        if attrs.get("external_id") is not None and not str(attrs["external_id"]).strip():
            attrs["external_id"] = None

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["is_expired"] = instance.is_expired
        return data

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


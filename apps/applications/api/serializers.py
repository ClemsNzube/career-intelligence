from rest_framework import serializers

from apps.applications.models import JobApplication
from apps.jobs.api.serializers import JobSerializer
from apps.jobs.models import Job


class JobApplicationSerializer(serializers.ModelSerializer):
    job = JobSerializer(read_only=True)
    job_id = serializers.PrimaryKeyRelatedField(
        source="job",
        queryset=Job.objects.all(),
        write_only=True,
        help_text="Use the job ID from a discovery or recommendation response to track that job.",
    )

    class Meta:
        model = JobApplication
        fields = [
            "id",
            "job",
            "job_id",
            "status",
            "applied_at",
            "follow_up_at",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        validators = []

    def validate(self, attrs):
        job = attrs.get("job", getattr(self.instance, "job", None))
        request = self.context.get("request")
        if job is not None and request is not None and request.user.is_authenticated:
            applications = JobApplication.objects.filter(user=request.user, job=job)
            if self.instance is not None:
                applications = applications.exclude(pk=self.instance.pk)
            if applications.exists():
                raise serializers.ValidationError(
                    {"job_id": "You are already tracking this job."}
                )
        return attrs


class ApplicationStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    saved = serializers.IntegerField()
    applied = serializers.IntegerField()
    interview = serializers.IntegerField()
    offer = serializers.IntegerField()
    rejected = serializers.IntegerField()
    withdrawn = serializers.IntegerField()


class ApplicationDashboardSerializer(serializers.Serializer):
    stats = ApplicationStatsSerializer()
    follow_ups = JobApplicationSerializer(many=True)
    applications = JobApplicationSerializer(many=True)

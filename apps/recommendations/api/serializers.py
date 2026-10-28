from rest_framework import serializers

from apps.jobs.api.serializers import JobSerializer


class RecommendationScoresSerializer(serializers.Serializer):
    rule = serializers.FloatField()
    semantic = serializers.FloatField(allow_null=True)
    final = serializers.FloatField()
    semantic_available = serializers.BooleanField()


class RecommendationExplanationSerializer(serializers.Serializer):
    summary = serializers.CharField()
    score_band = serializers.CharField()
    strengths = serializers.ListField(child=serializers.CharField())
    gaps = serializers.ListField(child=serializers.CharField())
    recommendation = serializers.CharField()
    matched_skills = serializers.ListField(child=serializers.CharField())
    missing_skills = serializers.ListField(child=serializers.CharField())


class RecommendationSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    score = serializers.FloatField()
    match = serializers.BooleanField()
    application_status = serializers.CharField(
        default="not_tracked",
        help_text=(
            "Current user's tracking status. To save a recommendation, POST its "
            "job.id to /api/applications/ as job_id."
        ),
    )
    job = JobSerializer(read_only=True)
    components = serializers.DictField(child=serializers.FloatField())
    scores = RecommendationScoresSerializer()
    explanation = RecommendationExplanationSerializer()
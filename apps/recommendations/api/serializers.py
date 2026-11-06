from rest_framework import serializers

from apps.jobs.api.serializers import JobSerializer


class RecommendationScoresSerializer(serializers.Serializer):
    rule = serializers.FloatField()
    semantic = serializers.FloatField(allow_null=True)
    final = serializers.FloatField()
    semantic_available = serializers.BooleanField()
    hybrid = serializers.FloatField(allow_null=True, default=None)
    ai = serializers.FloatField(allow_null=True, default=None)


class RecommendationExplanationSerializer(serializers.Serializer):
    summary = serializers.CharField()
    score_band = serializers.CharField()
    strengths = serializers.ListField(child=serializers.CharField())
    gaps = serializers.ListField(child=serializers.CharField())
    recommendation = serializers.CharField()
    matched_skills = serializers.ListField(child=serializers.CharField())
    missing_skills = serializers.ListField(child=serializers.CharField())


class CandidateJobEvidenceSerializer(serializers.Serializer):
    candidate_quote = serializers.CharField(allow_blank=True)
    job_quote = serializers.CharField(allow_blank=True)


class AIJobEvaluationSerializer(serializers.Serializer):
    suitability_score = serializers.IntegerField(min_value=0, max_value=100)
    strengths = serializers.ListField(child=serializers.CharField())
    missing_requirements = serializers.ListField(child=serializers.CharField())
    concerns = serializers.ListField(child=serializers.CharField())
    explanation = serializers.CharField()
    evidence = CandidateJobEvidenceSerializer(many=True)
    hybrid_score = serializers.FloatField(min_value=0, max_value=1)
    blended_score = serializers.FloatField(min_value=0, max_value=1)


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
    ai_evaluation = AIJobEvaluationSerializer(allow_null=True, default=None)
    job = JobSerializer(read_only=True)
    components = serializers.DictField(child=serializers.FloatField())
    scores = RecommendationScoresSerializer()
    explanation = RecommendationExplanationSerializer()
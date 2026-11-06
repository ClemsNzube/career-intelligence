import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.applications.models import JobApplication
from apps.intelligence.ai.providers import get_intelligence_provider
from apps.intelligence.ai.providers.base import (
    AIProviderConfigurationError,
    AIProviderError,
    AIProviderUnavailableError,
)
from apps.jobs.models import Job
from apps.recommendations.api.serializers import RecommendationSerializer
from apps.recommendations.services.recommend_jobs import DEFAULT_RECOMMENDATION_LIMIT, get_recommended_jobs
from apps.users.models import CVDocument

logger = logging.getLogger(__name__)
AI_RERANK_SHORTLIST_SIZE = 10
AI_BLEND_WEIGHT = 0.25


class RecommendationPagination(PageNumberPagination):
    page_size = DEFAULT_RECOMMENDATION_LIMIT
    page_size_query_param = "limit"
    max_page_size = 50


class JobRecommendationsAPIView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = RecommendationPagination
    serializer_class = RecommendationSerializer
    # Recommendations are computed dynamically; DRF's browsable API still expects a queryset.
    queryset = Job.objects.none()

    @extend_schema(
        summary="Get ranked job recommendations",
        description=(
            "Return recommendations using rule-based and semantic matching. "
            "Set include_ai=true to explicitly evaluate and rerank the top ten "
            "hybrid results against the user's latest approved CV, blending the "
            "hybrid score (75%) with AI suitability (25%). The configured provider "
            "is selected with AI_PROVIDER."
        ),
        parameters=[
            OpenApiParameter(
                "include_ai",
                OpenApiTypes.STR,
                enum=["true", "false"],
                description=(
                    "Opt in to AI evaluation of the approved CV and top ten jobs. "
                    "Requires a configured AI provider and an approved CV."
                ),
            )
        ],
        responses=RecommendationSerializer,
        tags=["Recommendations"],
    )
    def get(self, request, *args, **kwargs):
        include_ai_value = request.query_params.get("include_ai", "false").lower()
        if include_ai_value not in {"true", "false"}:
            return Response(
                {"detail": "include_ai must be true or false."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        include_ai = include_ai_value == "true"
        raw_limit = request.query_params.get("limit")
        if raw_limit is not None:
            try:
                limit = int(raw_limit)
            except ValueError:
                return Response({"detail": "limit must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
            if limit < 1 or limit > RecommendationPagination.max_page_size:
                return Response(
                    {"detail": f"limit must be between 1 and {RecommendationPagination.max_page_size}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if include_ai and request.query_params.get("page", "1") != "1":
            return Response(
                {
                    "detail": (
                        "AI reranking is limited to the first page of the top "
                        f"{AI_RERANK_SHORTLIST_SIZE} hybrid recommendations."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        recommendations = get_recommended_jobs(request.user, limit=None)
        if recommendations is None:
            return Response({"detail": "No career profile found for this user."}, status=status.HTTP_404_NOT_FOUND)

        if include_ai:
            try:
                provider = get_intelligence_provider()
            except AIProviderConfigurationError as exc:
                return Response(
                    {"detail": str(exc)},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            candidate_document = (
                CVDocument.objects.filter(
                    user=request.user,
                    status=CVDocument.Status.APPROVED,
                )
                .order_by("-reviewed_at", "-pk")
                .first()
            )
            if candidate_document is None:
                return Response(
                    {
                        "detail": (
                            "Approve a CV before requesting AI job evaluations."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            try:
                shortlist = recommendations[:AI_RERANK_SHORTLIST_SIZE]
                evaluations = provider.evaluate_jobs(
                    candidate_text=candidate_document.extracted_text,
                    candidate_data=candidate_document.extracted_data,
                    jobs=[item["job"] for item in shortlist],
                )
            except AIProviderConfigurationError as exc:
                return Response(
                    {"detail": str(exc)},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            except AIProviderUnavailableError as exc:
                logger.warning(
                    "AI recommendation provider unavailable for user_id=%s",
                    request.user.pk,
                )
                return Response(
                    {"detail": str(exc)},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            except AIProviderError:
                logger.exception("AI recommendation evaluation failed for user_id=%s", request.user.pk)
                return Response(
                    {"detail": "AI evaluation failed. Retry the request later."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            for recommendation in shortlist:
                job_id = recommendation["job"].pk
                evaluation = evaluations[job_id]
                hybrid_score = recommendation["score"]
                evaluation["hybrid_score"] = hybrid_score
                blended_score = (
                    hybrid_score * (1 - AI_BLEND_WEIGHT)
                    + (evaluation["suitability_score"] / 100) * AI_BLEND_WEIGHT
                )
                evaluation["blended_score"] = blended_score
                recommendation["score"] = blended_score
                recommendation["match"] = blended_score >= 0.5
                recommendation["ai_evaluation"] = evaluation
                recommendation["scores"]["hybrid"] = hybrid_score
                recommendation["scores"]["ai"] = (
                    evaluation["suitability_score"] / 100
                )
                recommendation["scores"]["final"] = blended_score

            shortlist.sort(
                key=lambda item: (
                    -item["score"],
                    item["job"].posted_at is None,
                    -(item["job"].posted_at.timestamp())
                    if item["job"].posted_at
                    else 0,
                    -item["job"].pk,
                )
            )
            recommendations = [
                {"rank": rank, **item}
                for rank, item in enumerate(shortlist, start=1)
            ]

        recommendation_job_ids = [item["job"].pk for item in recommendations]
        application_statuses = dict(
            JobApplication.objects.filter(
                user=request.user,
                job_id__in=recommendation_job_ids,
            ).values_list("job_id", "status")
        )
        for recommendation in recommendations:
            recommendation["application_status"] = application_statuses.get(
                recommendation["job"].pk,
                "not_tracked",
            )

        page = self.paginate_queryset(recommendations)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
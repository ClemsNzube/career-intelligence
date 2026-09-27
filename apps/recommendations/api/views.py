from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.recommendations.api.serializers import RecommendationSerializer
from apps.recommendations.services.recommend_jobs import DEFAULT_RECOMMENDATION_LIMIT, get_recommended_jobs


class RecommendationPagination(PageNumberPagination):
    page_size = DEFAULT_RECOMMENDATION_LIMIT
    page_size_query_param = "limit"
    max_page_size = 50


class JobRecommendationsAPIView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = RecommendationPagination
    serializer_class = RecommendationSerializer

    def get(self, request, *args, **kwargs):
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

        recommendations = get_recommended_jobs(request.user, limit=None)
        if recommendations is None:
            return Response({"detail": "No career profile found for this user."}, status=status.HTTP_404_NOT_FOUND)

        page = self.paginate_queryset(recommendations)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
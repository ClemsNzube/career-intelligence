from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.recommendations.api.serializers import RecommendationSerializer
from apps.recommendations.services.recommend_jobs import DEFAULT_RECOMMENDATION_LIMIT, get_recommended_jobs


class JobRecommendationsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    default_limit = DEFAULT_RECOMMENDATION_LIMIT
    max_limit = 50

    def get(self, request, *args, **kwargs):
        raw_limit = request.query_params.get("limit", self.default_limit)
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            return Response({"detail": "limit must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        if limit < 1 or limit > self.max_limit:
            return Response(
                {"detail": f"limit must be between 1 and {self.max_limit}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recommendations = get_recommended_jobs(request.user, limit=limit)
        if recommendations is None:
            return Response({"detail": "No career profile found for this user."}, status=status.HTTP_404_NOT_FOUND)

        serializer = RecommendationSerializer(recommendations, many=True)
        return Response({"count": len(recommendations), "results": serializer.data}, status=status.HTTP_200_OK)
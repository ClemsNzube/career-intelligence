from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema


job_list_schema = extend_schema(
    tags=["Jobs"],
    summary="List and create jobs",
    description=(
        "Retrieve a paginated list of active jobs or create a job posting. "
        "Combine title, company, location, skills, work_type, and employment_type "
        "filters to discover relevant opportunities. The search parameter also "
        "matches title, company, description, location, and skill names."
    ),
    parameters=[
        OpenApiParameter("search", OpenApiTypes.STR, description="Search across title, company, description, location, and skills."),
        OpenApiParameter("title", OpenApiTypes.STR, description="Filter by a partial job title."),
        OpenApiParameter("company", OpenApiTypes.STR, description="Filter by a partial company name."),
        OpenApiParameter("location", OpenApiTypes.STR, description="Filter by a partial location."),
        OpenApiParameter(
            "skills",
            OpenApiTypes.STR,
            many=True,
            description="Filter by one or more exact skill names; repeat the parameter or provide comma-separated names.",
        ),
    ],
    examples=[
        OpenApiExample(
            "Job creation example",
            value={
                "title": "Senior Python Developer",
                "company_name": "Example Corp",
                "description": "Build and maintain backend services.",
                "location": "Remote",
                "work_type": "remote",
                "employment_type": "full_time",
                "application_url": "https://example.com/jobs/123",
                "source": "linkedin",
                "external_id": "linkedin-123",
                "skills": ["Python", "Django", "PostgreSQL"],
            },
            request_only=True,
            response_only=False,
        )
    ],
)

job_detail_schema = extend_schema(
    tags=["Jobs"],
    summary="Retrieve, update, or delete a job",
    description="Fetch a single job, update it, or delete it permanently.",
)

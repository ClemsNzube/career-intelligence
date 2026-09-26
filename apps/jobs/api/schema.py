from drf_spectacular.utils import OpenApiExample, extend_schema


job_list_schema = extend_schema(
    tags=["Jobs"],
    summary="List and create jobs",
    description="Retrieve a paginated list of jobs or create a new job posting.",
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

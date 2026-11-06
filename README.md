# Career Intelligence

Career Intelligence is a Django REST API for managing career profiles and job
postings, matching candidates to roles, and returning ranked job recommendations
with deterministic explanations.

## Features

- Career profiles, preferences, skills, experience, education, certifications,
  and projects.
- Private PDF/DOCX CV uploads with text extraction, editable structured
  suggestions, and explicit approval before candidate-profile updates.
- Job listing, filtering, management, and ingestion endpoints.
- Per-source listing provenance, original source/application links, and
  cross-source duplicate consolidation.
- Rule-based matching across skills, experience, work type, location, and title.
- Hybrid recommendations combining rule-based scores (60%) and semantic
  similarity (40%) when both profile and job embeddings are available.
- Human-readable match summaries, strengths, and gaps.
- Rule-score fallback when embeddings are missing. Missing data is marked in
  the response rather than silently treated as zero semantic similarity.
- Idempotent command to create embeddings for profiles and jobs that do not
  already have one.

## Tech stack

- Python 3.12+
- Django 6.1 and Django REST Framework
- PostgreSQL 16 with the `pgvector` extension
- FastEmbed (`BAAI/bge-small-en-v1.5`) for local embedding generation

## Local setup

### 1. Install dependencies

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 2. Start PostgreSQL

The included Compose file starts PostgreSQL with pgvector on host port `5433`:

```bash
docker compose up -d db
```

For local development, the Compose service is configured with:

| Setting | Value |
| --- | --- |
| Database | `career_intelligence` |
| User | `career_user` |
| Password | `career_password` |
| Host port | `5433` |

These credentials are for local development only. Do not reuse them in
production.

### 3. Configure environment

Create a `.env` file in the repository root. It is loaded by the Django
settings; keep secrets out of version control.

```dotenv
DJANGO_SECRET_KEY=replace-with-a-random-secret
DJANGO_DEBUG=True
POSTGRES_DB=career_intelligence
POSTGRES_USER=career_user
POSTGRES_PASSWORD=career_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT=120
```

Generate a suitable local secret with:

```bash
openssl rand -hex 32
```

### 4. Apply migrations and start Django

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The API is available at `http://127.0.0.1:8000/`. The interactive API schema is
at `http://127.0.0.1:8000/api/docs/`.

## API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health/` | Health check |
| `GET`, `POST` | `/api/profiles/` | List or create career profiles |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/profiles/{id}/` | Manage a career profile |
| `GET`, `POST` | `/api/preferences/` | List or create career preferences |
| `GET`, `POST` | `/api/education/` | List or create education entries |
| `GET`, `POST` | `/api/experience/` | List or create experience entries |
| `GET`, `POST` | `/api/certifications/` | List or create certifications |
| `GET`, `POST` | `/api/projects/` | List or create projects |
| `GET`, `POST` | `/api/jobs/` | List or create jobs |
| `POST` | `/api/jobs/ingest/` | Ingest job postings |
| `GET` | `/api/jobs/{id}/match/` | Get a rule-based match for one job |
| `GET` | `/api/recommendations/` | Get the authenticated user's ranked recommendations |
| `GET`, `POST` | `/api/cvs/` | List or upload the authenticated user's CVs |
| `GET`, `PATCH`, `DELETE` | `/api/cvs/{id}/` | Review/edit extraction or delete a CV |
| `GET` | `/api/cvs/{id}/download/` | Download the original CV |
| `POST` | `/api/cvs/{id}/approve/` | Apply reviewed summary and known skills to the career profile |
| `GET`, `POST` | `/api/applications/` | List or track jobs for the authenticated user |
| `GET` | `/api/applications/dashboard/` | Get tracking counts, scheduled follow-ups, and recent applications |
| `GET` | `/api/applications/follow-ups/` | Get due or overdue follow-ups |
| `GET` | `/api/applications/stats/` | Get application-status counts |

### CV upload and review

Upload a PDF or DOCX as multipart form data using the `file` field. Files are
limited to 10 MB. Text is extracted locally; scanned PDFs that require OCR are
reported as failed rather than sent to an external service. Extracted sections
are saved as editable candidate suggestions and do not change a career profile
until the owner calls the approve endpoint. Original CV downloads are served
through an authenticated, owner-scoped endpoint.

The default candidate extractor is rule-based and does not require an LLM. CV
text is not sent to OpenAI or Ollama unless
`CV_CANDIDATE_INTELLIGENCE_PROVIDER` is explicitly configured. To use Ollama
for CV interpretation, run Ollama locally, pull the configured model, and set:

```dotenv
CV_CANDIDATE_INTELLIGENCE_PROVIDER=apps.intelligence.ai.providers.ollama.OllamaIntelligenceProvider
```

The original CV remains private, and extracted suggestions still require user
review and approval before updating the career profile.

### Optional AI job evaluation

The default AI provider is local Ollama. Install Ollama using its official
instructions, then start the Ollama service and download the configured model:

```bash
ollama pull qwen2.5:7b
```

The app connects to `OLLAMA_BASE_URL` (default `http://localhost:11434`), using
`OLLAMA_MODEL` and a bounded `OLLAMA_TIMEOUT`. No Ollama request is made during
normal recommendations. To opt in, call
`GET /api/recommendations/?include_ai=true` with an approved CV. Ollama
evaluates and reranks up to ten hybrid recommendations, blending the existing
hybrid score (75%) with AI suitability (25%). If Ollama is not running or the
model is missing, the endpoint returns an explicit service-unavailable error;
it does not silently switch providers or alter the ordinary recommendation
scores.

To select OpenAI instead, set `AI_PROVIDER=openai` and configure
`OPENAI_API_KEY` and optionally `OPENAI_MODEL`. OpenAI is never selected
automatically. OpenAI evaluation sends the approved CV text and job descriptions
to OpenAI and may incur API charges. Requests without `include_ai=true` make no
LLM call and preserve existing scores and ranking.

The recommendation endpoint requires authentication and a career profile for
the authenticated user. Use `?limit=10` to request a page size from 1 to 50;
pagination links and total count are returned by the API.

Example request using HTTP Basic authentication:

```bash
curl -u 'your-username' \
  'http://127.0.0.1:8000/api/recommendations/?limit=10'
```

## Recommendations and embeddings

Each recommendation includes the job details, rank, rule components, scores,
and a deterministic explanation. `scores.final` is the ranking score and
`score` is retained as a compatibility field:

```json
{
  "rank": 1,
  "score": 0.82,
  "match": true,
  "scores": {
    "rule": 0.74,
    "semantic": 0.94,
    "final": 0.82,
    "semantic_available": true
  },
  "explanation": {
    "summary": "Strong match for this role.",
    "score_band": "Strong match",
    "strengths": ["Strong semantic similarity"],
    "gaps": [],
    "recommendation": "Apply",
    "matched_skills": ["Python"],
    "missing_skills": []
  }
}
```

The hybrid score uses `0.6 * rule + 0.4 * semantic`. Cosine similarities below
zero are floored at zero before blending. If the profile or job has no saved
embedding, the final score falls back to the rule score, `semantic` is `null`,
and `semantic_available` is `false`.

Generate embeddings for profiles and jobs that are missing one:

```bash
python manage.py backfill_embeddings
```

The command skips existing embeddings and reports objects without usable text.
It is safe to run repeatedly to embed newly added objects. Existing embeddings
are not refreshed when profile or job text changes; regenerate them through
`EmbeddingService.save_for_object()` when needed. The first run may download
the FastEmbed model.

## Tests

Run the intelligence, matching, and recommendation tests:

```bash
python manage.py test \
  apps.intelligence.embeddings.tests \
  apps.intelligence.explanations.tests \
  apps.intelligence.matching.tests \
  apps.intelligence.similarity.tests \
  apps.recommendations.tests.test_recommendations \
  apps.matching.tests.test_matching_engine
```

## Project layout

```text
apps/
  intelligence/    Embedding, semantic similarity, explanations, hybrid matching
  jobs/            Job models and API
  matching/        Rule-based matchers and scoring
  recommendations/ Ranked recommendation API
  skills/          Shared skill data
  users/           Career profiles and preferences
config/            Django project settings and root URLs
```

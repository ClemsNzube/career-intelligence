import json
import logging
from types import SimpleNamespace
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

from apps.intelligence.ai.providers.base import (
    AIProviderConfigurationError,
    AIProviderError,
    AIProviderUnavailableError,
)
from apps.intelligence.ai.providers.structured import StructuredIntelligenceProvider

logger = logging.getLogger(__name__)


class OllamaIntelligenceProvider(StructuredIntelligenceProvider):
    """Local Ollama provider implementing the shared structured-AI contract."""

    provider_name = "ollama"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ):
        self.base_url = (
            base_url or getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        ).rstrip("/")
        self.model = model or getattr(settings, "OLLAMA_MODEL", "qwen2.5:7b")
        self.timeout = timeout or getattr(settings, "OLLAMA_TIMEOUT", 120)
        if self.timeout <= 0:
            raise AIProviderConfigurationError("OLLAMA_TIMEOUT must be greater than zero.")

    @staticmethod
    def _response_format(payload: dict[str, Any]) -> str | dict[str, Any]:
        jobs = payload.get("jobs")
        if not isinstance(payload.get("candidate"), dict) or not isinstance(jobs, list):
            return "json"

        evidence_schema = {
            "type": "object",
            "properties": {
                "candidate_quote": {"type": "string"},
                "job_quote": {"type": "string"},
            },
            "required": ["candidate_quote", "job_quote"],
            "additionalProperties": False,
        }
        evaluation_schema = {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "integer",
                    "enum": [job["id"] for job in jobs],
                },
                "suitability_score": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                },
                "strengths": {"type": "array", "items": {"type": "string"}},
                "missing_requirements": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "concerns": {"type": "array", "items": {"type": "string"}},
                "explanation": {"type": "string"},
                "evidence": {
                    "type": "array",
                    "items": evidence_schema,
                    "maxItems": 20,
                },
            },
            "required": [
                "job_id",
                "suitability_score",
                "strengths",
                "missing_requirements",
                "concerns",
                "explanation",
                "evidence",
            ],
            "additionalProperties": False,
        }
        return {
            "type": "object",
            "properties": {
                "evaluations": {
                    "type": "array",
                    "items": evaluation_schema,
                    "minItems": len(jobs),
                    "maxItems": len(jobs),
                }
            },
            "required": ["evaluations"],
            "additionalProperties": False,
        }

    def _complete_json(self, system_prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(
            {
                "model": self.model,
                "stream": False,
                "format": self._response_format(payload),
                "options": {
                    "temperature": 0,
                    "num_ctx": 4096,
                    "num_predict": 768,
                },
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=False),
                    },
                ],
            }
        ).encode("utf-8")
        request = Request(
            f"{self.base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_data = json.loads(response.read())
        except HTTPError as exc:
            logger.warning("Ollama returned HTTP status %s", exc.code)
            if exc.code in {404, 502, 503, 504}:
                raise AIProviderUnavailableError(
                    "Ollama is unavailable or the configured model is not installed."
                ) from exc
            raise AIProviderError(
                f"Ollama rejected the request with HTTP status {exc.code}."
            ) from exc
        except TimeoutError as exc:
            logger.warning(
                "Ollama inference timed out after %s seconds",
                self.timeout,
            )
            raise AIProviderUnavailableError(
                f"Ollama did not finish its response within {self.timeout:g} seconds. "
                "The local model may be too slow for this evaluation; try again or use fewer jobs."
            ) from exc
        except (URLError, ConnectionError) as exc:
            logger.warning("Ollama connection failed: %s", exc.__class__.__name__)
            raise AIProviderUnavailableError(
                "Cannot connect to Ollama. Start Ollama and ensure the configured model is available."
            ) from exc
        except OSError as exc:
            logger.warning("Ollama response could not be read: %s", exc.__class__.__name__)
            raise AIProviderUnavailableError(
                "Ollama could not complete the request. Check that the local service is running."
            ) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise AIProviderError("Ollama returned an invalid response.") from exc

        if not isinstance(response_data, dict):
            raise AIProviderError("Ollama returned an invalid response object.")
        message = response_data.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        try:
            result = json.loads(content or "")
        except (TypeError, json.JSONDecodeError) as exc:
            raise AIProviderError("Ollama returned invalid JSON content.") from exc
        if not isinstance(result, dict):
            raise AIProviderError("Ollama response content must be a JSON object.")
        if "candidate" in payload and isinstance(result.get("evaluations"), list):
            candidate_text = payload["candidate"].get("cv_evidence", "")
            jobs_by_id = {job["id"]: job for job in payload.get("jobs", [])}
            for evaluation in result["evaluations"]:
                if not isinstance(evaluation, dict):
                    continue
                job = jobs_by_id.get(evaluation.get("job_id"))
                for evidence in evaluation.get("evidence", []):
                    if not isinstance(evidence, dict) or "candidate_quote" in evidence:
                        continue
                    content = evidence.get("content")
                    evidence_type = evidence.get("type")
                    if (
                        isinstance(content, str)
                        and evidence_type in {"candidate", "resume"}
                        and content.casefold() in candidate_text.casefold()
                    ):
                        evidence.clear()
                        evidence.update(candidate_quote=content, job_quote="")
                    elif (
                        isinstance(content, str)
                        and evidence_type == "job"
                        and job is not None
                        and content.casefold()
                        in job.get("description", "").casefold()
                    ):
                        evidence.clear()
                        evidence.update(candidate_quote="", job_quote=content)
        return result

    def evaluate_jobs(
        self,
        candidate_text: str,
        candidate_data: dict[str, Any],
        jobs: list[Any],
    ) -> dict[int, dict[str, Any]]:
        compact_candidate_data = self._compact_candidate_data(candidate_data)
        compact_jobs = []
        for job in jobs:
            skill_names = list(job.skills.values_list("name", flat=True))[:15]
            compact_jobs.append(
                SimpleNamespace(
                    pk=job.pk,
                    title=job.title[:200],
                    company_name=job.company_name[:200],
                    description=job.description[:1_200],
                    min_years_experience=job.min_years_experience,
                    skills=SimpleNamespace(
                        values_list=lambda *args, _names=skill_names, **kwargs: _names
                    ),
                )
            )
        return super().evaluate_jobs(
            candidate_text=candidate_text[:3_000],
            candidate_data=compact_candidate_data,
            jobs=compact_jobs,
        )

    @staticmethod
    def _compact_candidate_data(candidate_data: dict[str, Any]) -> dict[str, Any]:
        compact = {}
        for field, limit in (
            ("summary", 250),
            ("career_level", 80),
        ):
            value = candidate_data.get(field)
            if isinstance(value, str) and value:
                compact[field] = value[:limit]
        for field, count, limit in (
            ("skills", 12, 60),
            ("transferable_skills", 4, 60),
            ("achievements", 4, 80),
        ):
            value = candidate_data.get(field)
            if isinstance(value, list):
                compact[field] = [
                    item[:limit] for item in value[:count] if isinstance(item, str)
                ]

        experiences = candidate_data.get("experience")
        if isinstance(experiences, list):
            compact["experience"] = [
                {
                    key: entry[key][:limit]
                    for key, limit in (
                        ("title", 100),
                        ("company", 100),
                        ("description", 160),
                    )
                    if isinstance(entry.get(key), str)
                }
                for entry in experiences[:2]
                if isinstance(entry, dict)
            ]
        education = candidate_data.get("education")
        if isinstance(education, list):
            compact["education"] = [
                {
                    key: entry[key][:100]
                    for key in ("institution", "degree", "field_of_study")
                    if isinstance(entry.get(key), str)
                }
                for entry in education[:1]
                if isinstance(entry, dict)
            ]
        projects = candidate_data.get("projects")
        if isinstance(projects, list):
            compact["projects"] = [
                {
                    key: entry[key][:100]
                    for key in ("name", "role", "description")
                    if isinstance(entry.get(key), str)
                }
                for entry in projects[:1]
                if isinstance(entry, dict)
            ]
        return compact

    def extract(self, text: str) -> dict[str, Any]:
        result = super().extract(text)
        result["extraction_method"] = "ollama"
        return result

from django.conf import settings
from django.utils.module_loading import import_string

from apps.users.models import CVDocument
from apps.users.services.cv_parser import (
    CVParseError,
    CandidateIntelligenceProvider,
    RuleBasedCandidateExtractor,
    extract_cv_text,
)
from apps.intelligence.ai.providers.base import AIProviderError


def process_cv_document(
    document: CVDocument,
    candidate_extractor: CandidateIntelligenceProvider | None = None,
) -> CVDocument:
    try:
        with document.file.open("rb") as uploaded_file:
            text = extract_cv_text(uploaded_file, document.original_filename)
        extractor = candidate_extractor
        provider_path = getattr(
            settings,
            "CV_CANDIDATE_INTELLIGENCE_PROVIDER",
            "",
        )
        if extractor is None and provider_path:
            provider_class = import_string(provider_path)
            extractor = provider_class()
        if extractor is None:
            extractor = RuleBasedCandidateExtractor()
        if not isinstance(extractor, CandidateIntelligenceProvider):
            raise TypeError(
                "The configured CV candidate extractor must implement "
                "CandidateIntelligenceProvider."
            )
        structured_data = extractor.extract(text)
        if not isinstance(structured_data, dict):
            raise TypeError("Candidate extractor must return a dictionary.")
    except (CVParseError, OSError, AIProviderError) as exc:
        document.status = CVDocument.Status.FAILED
        document.error_message = (
            str(exc)
            if isinstance(exc, (CVParseError, AIProviderError))
            else "The original CV file could not be read from storage."
        )
        document.save(update_fields=["status", "error_message", "updated_at"])
        return document

    document.extracted_text = text
    document.extracted_data = structured_data
    document.status = CVDocument.Status.REVIEW
    document.error_message = ""
    document.save(
        update_fields=[
            "extracted_text",
            "extracted_data",
            "status",
            "error_message",
            "updated_at",
        ]
    )
    return document

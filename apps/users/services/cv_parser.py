import re
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.oxml.exceptions import InvalidXmlError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from apps.skills.models import Skill

MAX_CV_BYTES = 10 * 1024 * 1024
MAX_EXTRACTED_CHARACTERS = 250_000
MAX_PDF_PAGES = 200
SECTION_NAMES = {
    "experience": {"experience", "work experience", "employment history", "work history"},
    "education": {"education", "academic background"},
    "projects": {"projects", "personal projects"},
    "skills": {"skills", "technical skills", "core competencies"},
}


class CVParseError(ValueError):
    pass


def validate_cv_upload(upload):
    filename = Path(upload.name).name
    extension = Path(filename).suffix.lower()
    if extension not in {".pdf", ".docx"}:
        raise CVParseError("Upload a PDF or DOCX file.")
    if upload.size == 0:
        raise CVParseError("The uploaded CV is empty.")
    if upload.size > MAX_CV_BYTES:
        raise CVParseError("CV files must be 10 MB or smaller.")

    header = upload.read(8)
    upload.seek(0)
    if extension == ".pdf" and not header.startswith(b"%PDF-"):
        raise CVParseError("The uploaded file is not a valid PDF.")
    if extension == ".docx":
        try:
            with zipfile.ZipFile(upload) as archive:
                entries = archive.infolist()
                if (
                    "word/document.xml" not in archive.namelist()
                    or len(entries) > 2_000
                    or sum(entry.file_size for entry in entries) > 30 * 1024 * 1024
                ):
                    raise CVParseError("The uploaded file is not a valid DOCX document.")
        except zipfile.BadZipFile as exc:
            raise CVParseError("The uploaded file is not a valid DOCX document.") from exc
        finally:
            upload.seek(0)
    return filename


def extract_cv_text(file_object, filename):
    extension = Path(filename).suffix.lower()
    try:
        if extension == ".pdf":
            reader = PdfReader(file_object)
            if reader.is_encrypted:
                raise CVParseError("Password-protected PDF files are not supported.")
            if len(reader.pages) > MAX_PDF_PAGES:
                raise CVParseError(
                    f"CV PDFs must contain {MAX_PDF_PAGES} pages or fewer."
                )
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif extension == ".docx":
            document = Document(file_object)
            text = "\n".join(
                paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()
            )
            for table in document.tables:
                for row in table.rows:
                    text += "\n" + " | ".join(cell.text.strip() for cell in row.cells)
        else:
            raise CVParseError("Upload a PDF or DOCX file.")
    except CVParseError:
        raise
    except (
        OSError,
        ValueError,
        TypeError,
        PdfReadError,
        PackageNotFoundError,
        InvalidXmlError,
        zipfile.BadZipFile,
    ) as exc:
        raise CVParseError("The CV could not be parsed. Check that the document is valid.") from exc

    text = text[:MAX_EXTRACTED_CHARACTERS].strip()
    if not text:
        raise CVParseError(
            "No text could be extracted. Scanned PDFs require OCR and are not supported yet."
        )
    return text


def _extract_sections(text):
    sections = {key: [] for key in SECTION_NAMES}
    current_section = None
    for raw_line in text.splitlines():
        line = raw_line.strip(" \t•*-")
        if not line:
            continue
        heading = re.sub(r"[:\s]+$", "", line.casefold())
        matched_section = next(
            (key for key, names in SECTION_NAMES.items() if heading in names),
            None,
        )
        if matched_section:
            current_section = matched_section
        elif current_section:
            sections[current_section].append(line)
    return sections


def _skill_items(lines):
    return {
        item.strip(" \t•*-")
        for line in lines
        for item in re.split(r"[,;|]", line)
        if item.strip(" \t•*-")
    }


class CandidateIntelligenceProvider(ABC):
    @abstractmethod
    def extract(self, text: str) -> dict[str, Any]:
        raise NotImplementedError


class RuleBasedCandidateExtractor(CandidateIntelligenceProvider):
    def extract(self, text: str) -> dict[str, Any]:
        sections = _extract_sections(text)
        catalog_skills = list(Skill.objects.all().only("name"))
        matched_skills = {
            skill.name
            for skill in catalog_skills
            if re.search(
                rf"(?<![\w+#.]){re.escape(skill.name)}(?![\w+#.])",
                text,
                re.IGNORECASE,
            )
        }
        matched_skills.update(_skill_items(sections["skills"]))
        return {
            "summary": "",
            "skills": sorted(matched_skills, key=str.casefold),
            "experience": [{"text": line} for line in sections["experience"]],
            "education": [{"text": line} for line in sections["education"]],
            "projects": [{"text": line} for line in sections["projects"]],
            "extraction_method": "rule_based",
            "review_required": True,
        }

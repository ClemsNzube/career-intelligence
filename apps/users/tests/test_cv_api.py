from io import BytesIO
import tempfile

from docx import Document
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from rest_framework import status
from rest_framework.test import APIClient

from apps.skills.models import Skill
from apps.users.models import CVDocument, CareerProfile


class CVDocumentAPITests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="cv-owner",
            email="cv-owner@example.com",
            password="test-password",
        )
        self.other_user = user_model.objects.create_user(
            username="other-cv-owner",
            email="other-cv-owner@example.com",
            password="test-password",
        )
        self.python = Skill.objects.create(name="Python", slug="python")
        self.django = Skill.objects.create(name="Django", slug="django")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.list_url = reverse("cv-list")

    @staticmethod
    def make_docx():
        document = Document()
        document.add_heading("Candidate", level=1)
        document.add_heading("Experience", level=2)
        document.add_paragraph("Backend Engineer at Example Corp, 2021-present")
        document.add_heading("Education", level=2)
        document.add_paragraph("BSc Computer Science, Example University")
        document.add_heading("Projects", level=2)
        document.add_paragraph("Career Intelligence platform")
        document.add_heading("Technical Skills", level=2)
        document.add_paragraph("Python, Django")
        output = BytesIO()
        document.save(output)
        return SimpleUploadedFile(
            "candidate.docx",
            output.getvalue(),
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
        )

    @staticmethod
    def make_pdf():
        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        font_reference = writer._add_object(font)
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {NameObject("/F1"): font_reference}
                )
            }
        )
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 72 720 Td (Python Engineer) Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
        output = BytesIO()
        writer.write(output)
        return SimpleUploadedFile(
            "candidate.pdf",
            output.getvalue(),
            content_type="application/pdf",
        )

    def test_docx_upload_extracts_reviewable_candidate_data_and_retains_original(self):
        response = self.client.post(
            self.list_url,
            {"file": self.make_docx()},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        document = CVDocument.objects.get(pk=response.data["id"])
        self.assertEqual(document.user, self.user)
        self.assertEqual(document.status, CVDocument.Status.REVIEW)
        self.assertEqual(document.original_filename, "candidate.docx")
        self.assertTrue(document.file.storage.exists(document.file.name))
        self.assertIn("Backend Engineer", document.extracted_text)
        self.assertIn("Python", document.extracted_data["skills"])
        self.assertIn("Django", document.extracted_data["skills"])
        self.assertEqual(
            document.extracted_data["experience"],
            [{"text": "Backend Engineer at Example Corp, 2021-present"}],
        )
        self.assertEqual(document.extracted_data["extraction_method"], "rule_based")
        self.assertTrue(document.extracted_data["review_required"])

    def test_pdf_upload_extracts_text_and_is_available_for_download(self):
        response = self.client.post(
            self.list_url,
            {"file": self.make_pdf()},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        document = CVDocument.objects.get(pk=response.data["id"])
        self.assertEqual(document.status, CVDocument.Status.REVIEW)
        self.assertIn("Python Engineer", document.extracted_text)
        download_response = self.client.get(
            reverse("cv-download", args=[document.pk])
        )
        self.assertEqual(download_response.status_code, status.HTTP_200_OK)
        self.assertEqual(download_response["Content-Type"], "application/pdf")

    def test_reviewed_extraction_can_be_corrected_then_approved(self):
        upload_response = self.client.post(
            self.list_url,
            {"file": self.make_docx()},
            format="multipart",
        )
        document_id = upload_response.data["id"]

        update_response = self.client.patch(
            reverse("cv-detail", args=[document_id]),
            {
                "extracted_data": {
                    "summary": "Backend engineer focused on Python services.",
                    "skills": ["Python", "Django"],
                    "experience": [{"title": "Backend Engineer"}],
                    "education": [],
                    "projects": [],
                }
            },
            format="json",
        )
        approve_response = self.client.post(
            reverse("cv-approve", args=[document_id]),
            {},
            format="json",
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        profile = CareerProfile.objects.get(user=self.user)
        self.assertEqual(profile.bio, "Backend engineer focused on Python services.")
        self.assertEqual(set(profile.skills.all()), {self.python, self.django})
        document = CVDocument.objects.get(pk=document_id)
        self.assertEqual(document.status, CVDocument.Status.APPROVED)
        self.assertIsNotNone(document.reviewed_at)

    def test_invalid_upload_is_rejected_and_unreadable_cv_is_marked_failed(self):
        invalid_response = self.client.post(
            self.list_url,
            {"file": SimpleUploadedFile("resume.txt", b"not a CV")},
            format="multipart",
        )
        empty_pdf_response = self.client.post(
            self.list_url,
            {"file": SimpleUploadedFile("scanned.pdf", b"%PDF-1.4\n%%EOF")},
            format="multipart",
        )

        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(empty_pdf_response.status_code, status.HTTP_201_CREATED)
        failed_document = CVDocument.objects.get(pk=empty_pdf_response.data["id"])
        self.assertEqual(failed_document.status, CVDocument.Status.FAILED)
        self.assertIn("could not be parsed", failed_document.error_message.lower())

    def test_download_and_document_access_are_limited_to_owner(self):
        upload_response = self.client.post(
            self.list_url,
            {"file": self.make_docx()},
            format="multipart",
        )
        document_id = upload_response.data["id"]
        document_url = reverse("cv-detail", args=[document_id])
        download_url = reverse("cv-download", args=[document_id])
        stored_file = CVDocument.objects.get(pk=document_id).file

        self.client.force_authenticate(user=self.other_user)
        detail_response = self.client.get(document_url)
        download_response = self.client.get(download_url)
        list_response = self.client.get(self.list_url)

        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(download_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(list_response.data["count"], 0)

        self.client.force_authenticate(user=self.user)
        delete_response = self.client.delete(document_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CVDocument.objects.filter(pk=document_id).exists())
        self.assertFalse(stored_file.storage.exists(stored_file.name))

    def test_cv_endpoints_require_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_deleting_user_removes_original_cv_file(self):
        response = self.client.post(
            self.list_url,
            {"file": self.make_docx()},
            format="multipart",
        )
        document = CVDocument.objects.get(pk=response.data["id"])
        stored_file = document.file

        self.user.delete()

        self.assertFalse(stored_file.storage.exists(stored_file.name))

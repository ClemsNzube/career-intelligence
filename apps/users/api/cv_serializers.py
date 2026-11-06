from pathlib import Path

from rest_framework import serializers

from apps.users.models import CVDocument
from apps.users.services.cv_parser import CVParseError, validate_cv_upload


class CVDocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = CVDocument
        fields = [
            "id",
            "file",
            "original_filename",
            "status",
            "extracted_data",
            "error_message",
            "created_at",
            "updated_at",
            "reviewed_at",
        ]
        read_only_fields = [
            "id",
            "original_filename",
            "status",
            "error_message",
            "created_at",
            "updated_at",
            "reviewed_at",
        ]

    def validate_file(self, value):
        try:
            validate_cv_upload(value)
        except CVParseError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value

    def validate_extracted_data(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Extracted candidate data must be an object.")
        return value

    def validate(self, attrs):
        if self.instance is None and "file" not in attrs:
            raise serializers.ValidationError({"file": "A CV file is required."})
        if self.instance and "file" in attrs:
            raise serializers.ValidationError(
                {"file": "Delete this CV and upload a new document to replace it."}
            )
        if self.instance and "extracted_data" in attrs:
            if self.instance.status != CVDocument.Status.REVIEW:
                raise serializers.ValidationError(
                    {"extracted_data": "Only CVs awaiting review can be edited."}
                )
        return attrs

    def create(self, validated_data):
        uploaded_file = validated_data["file"]
        document = CVDocument.objects.create(
            user=self.context["request"].user,
            file=uploaded_file,
            original_filename=Path(uploaded_file.name).name[:255],
            status=CVDocument.Status.PROCESSING,
        )
        from apps.users.services.cv_processing import process_cv_document

        return process_cv_document(document)

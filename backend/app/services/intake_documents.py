import base64
import binascii

from fastapi import HTTPException
from sqlalchemy import select

from app.audit.service import audit
from app.models.clients import IntakeDocument, Referral
from app.repositories.care import CareRepository


class IntakeDocuments:
    def __init__(self, db, request, actor):
        self.db, self.request, self.actor = db, request, actor
        self.repo = CareRepository(db, actor)

    def upload(self, data, client_id=None, referral_id=None):
        if referral_id:
            client_id = self.repo.require(Referral, referral_id).client_id
        client = self.repo.client(client_id, lock=True)
        try:
            content = base64.b64decode(data.content_base64, validate=True)
        except (ValueError, binascii.Error):
            raise HTTPException(422, "Invalid file encoding") from None
        if len(content) > (5 if referral_id else 3) * 1024 * 1024:
            raise HTTPException(413, "File exceeds the allowed size")
        from app.services.file_validation import validate_pdf, validate_photo

        if referral_id:
            content, mime = validate_pdf(content), "application/pdf"
        else:
            content, mime = validate_photo(content)
        endings = {
            "application/pdf": (".pdf",),
            "image/png": (".png",),
            "image/jpeg": (".jpg", ".jpeg"),
        }
        if not data.filename.lower().endswith(endings[mime]):
            raise HTTPException(422, "Filename extension must match the file type")
        category = "REFERRAL" if referral_id else "PHOTO"
        existing = self.db.scalar(
            select(IntakeDocument.version)
            .where(IntakeDocument.client_id == client.id, IntakeDocument.category == category)
            .order_by(IntakeDocument.version.desc())
            .limit(1)
        )
        row = IntakeDocument(
            facility_id=self.actor.facility_id,
            client_id=client.id,
            referral_id=referral_id,
            category=category,
            filename=data.filename,
            content=content,
            mime_type=mime,
            size=len(content),
            description=data.description,
            version=(existing or 0) + 1,
            created_by=self.actor.id,
        )
        self.db.add(row)
        self.db.flush()
        if not referral_id:
            client.photo_reference = str(row.id)
            client.updated_by = self.actor.id
        audit(
            self.db,
            self.request,
            "document.uploaded",
            "intake_document",
            self.actor,
            row.id,
            new={"category": row.category, "version": row.version, "size": row.size},
        )
        return row

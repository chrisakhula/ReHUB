from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import Field
from sqlalchemy.orm import Session

from app.audit.service import audit
from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.clients import ClientRevision, IntakeDocument, Referral
from app.repositories.clients import ClientRepository
from app.schemas.care import CareModel, care_paging
from app.services.intake_documents import IntakeDocuments

router = APIRouter(tags=["Private intake documents"])


class DocumentIn(CareModel):
    filename: str = Field(min_length=1, max_length=150, pattern=r"^[A-Za-z0-9][A-Za-z0-9 _().-]+$")
    content_base64: str = Field(min_length=4, max_length=7_000_000)
    description: str = Field(default="", max_length=500)


def metadata(row):
    return {col.key: getattr(row, col.key) for col in row.__table__.columns if col.key != "content"}


@router.post("/clients/{record_id}/photo", status_code=201)
def photo(
    record_id: UUID,
    data: DocumentIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("client.update")),
):
    return metadata(IntakeDocuments(db, request, actor).upload(data, client_id=record_id))


@router.post("/referrals/{record_id}/documents", status_code=201)
def referral_document(
    record_id: UUID,
    data: DocumentIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("referral.create")),
):
    return metadata(IntakeDocuments(db, request, actor).upload(data, referral_id=record_id))


@router.get("/referrals/{record_id}/documents")
def referral_documents(
    record_id: UUID,
    request: Request,
    paging=Depends(care_paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("referral.view")),
):
    repo = ClientRepository(db, actor)
    repo.require(Referral, record_id)
    rows, meta = repo.page(
        IntakeDocument, **paging, filters=(IntakeDocument.referral_id == record_id,)
    )
    audit(db, request, "document.list_accessed", "referral", actor, record_id)
    return {"items": [metadata(row) for row in rows], "meta": meta}


@router.get("/intake/documents/{record_id}")
def download(
    record_id: UUID,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("client.view")),
):
    from fastapi import HTTPException

    from app.core.security import permission_codes

    row = ClientRepository(db, actor).require(IntakeDocument, record_id)
    if row.referral_id and "referral.view" not in permission_codes(actor):
        raise HTTPException(403, "Referral access is required")
    audit(db, request, "document.accessed", "intake_document", actor, row.id)
    return Response(
        row.content,
        media_type=row.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{row.filename}"',
            "Content-Security-Policy": "sandbox",
        },
    )


@router.get("/clients/{record_id}/history")
def client_history(
    record_id: UUID,
    request: Request,
    paging=Depends(care_paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("client.view")),
):
    repo = ClientRepository(db, actor)
    repo.client(record_id)
    rows, meta = repo.page(
        ClientRevision, **paging, filters=(ClientRevision.client_id == record_id,)
    )
    audit(db, request, "client.history_accessed", "client", actor, record_id)
    return {"items": [metadata(row) for row in rows], "meta": meta}

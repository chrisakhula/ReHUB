"""ODPC Data Protection and Privacy API Routes (Kenya Data Protection Act 2019)."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.identity import User
from app.schemas.privacy import (
    DataBreachCreate,
    DataBreachOut,
    DataBreachSignoff,
    DataBreachUpdate,
    DataSubjectRequestCreate,
    DataSubjectRequestOut,
    DataSubjectRequestReview,
    ExportRequestApprove,
    ExportRequestCreate,
    ExportRequestOut,
    RetentionPolicyOut,
)
from app.services.privacy import PrivacyService

router = APIRouter(prefix="/privacy", tags=["ODPC Privacy & Data Protection"])


# --- Data Subject Requests (DSAR) ---
@router.post("/requests", response_model=DataSubjectRequestOut, status_code=status.HTTP_201_CREATED)
def create_data_subject_request(
    payload: DataSubjectRequestCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("privacy.manage")),
):
    svc = PrivacyService(db, actor)
    return svc.create_dsar(payload)


@router.get("/requests", response_model=List[DataSubjectRequestOut])
def list_data_subject_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("privacy.view")),
):
    svc = PrivacyService(db, actor)
    return svc.list_dsar(status=status_filter)


@router.put("/requests/{request_id}/review", response_model=DataSubjectRequestOut)
def review_data_subject_request(
    request_id: uuid.UUID,
    payload: DataSubjectRequestReview,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("privacy.dpo")),
):
    svc = PrivacyService(db, actor)
    try:
        return svc.review_dsar(request_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Data Breach Register ---
@router.post("/breaches", response_model=DataBreachOut, status_code=status.HTTP_201_CREATED)
def create_data_breach_incident(
    payload: DataBreachCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("privacy.manage")),
):
    svc = PrivacyService(db, actor)
    return svc.create_breach(payload)


@router.get("/breaches", response_model=List[DataBreachOut])
def list_data_breach_incidents(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("privacy.view")),
):
    svc = PrivacyService(db, actor)
    return svc.list_breaches()


@router.put("/breaches/{breach_id}", response_model=DataBreachOut)
def update_data_breach_incident(
    breach_id: uuid.UUID,
    payload: DataBreachUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("privacy.manage")),
):
    svc = PrivacyService(db, actor)
    try:
        return svc.update_breach(breach_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/breaches/{breach_id}/signoff", response_model=DataBreachOut)
def signoff_data_breach(
    breach_id: uuid.UUID,
    payload: DataBreachSignoff,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("privacy.dpo")),
):
    svc = PrivacyService(db, actor)
    try:
        return svc.signoff_breach(breach_id, payload.dpo_notes)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Retention Policies ---
@router.get("/retention", response_model=List[RetentionPolicyOut])
def list_retention_policies(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("privacy.view")),
):
    svc = PrivacyService(db, actor)
    return svc.list_retention_policies()


@router.post("/retention/seed", response_model=List[RetentionPolicyOut])
def seed_default_retention_policies(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("privacy.dpo")),
):
    svc = PrivacyService(db, actor)
    return svc.seed_default_retention_policies()


# --- Controlled Export Requests ---
@router.post("/exports", response_model=ExportRequestOut, status_code=status.HTTP_201_CREATED)
def request_bulk_export(
    payload: ExportRequestCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("privacy.view")),
):
    # Enforce domain-specific export permission if applicable
    perm_map = {
        "CLIENT_BULK": "client.export",
        "CLINICAL_BULK": "clinical.export",
        "FINANCE_BULK": "finance.export",
        "REPORTS_BULK": "reports.export",
    }
    required_perm = perm_map.get(payload.export_type)
    if required_perm:
        user_perms = {p.code for p in actor.permissions}
        for r in actor.roles:
            for p in r.permissions:
                user_perms.add(p.code)
        if required_perm not in user_perms and "admin" not in [r.name for r in actor.roles]:
            raise HTTPException(
                status_code=403,
                detail=f"Missing explicit export authorization: '{required_perm}' required for {payload.export_type}",
            )

    svc = PrivacyService(db, actor)
    return svc.request_export(payload)


@router.get("/exports", response_model=List[ExportRequestOut])
def list_bulk_export_requests(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("privacy.view")),
):
    svc = PrivacyService(db, actor)
    return svc.list_exports()


@router.post("/exports/{export_id}/approve", response_model=ExportRequestOut)
def approve_bulk_export(
    export_id: uuid.UUID,
    payload: ExportRequestApprove,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("privacy.dpo")),
):
    svc = PrivacyService(db, actor)
    try:
        return svc.approve_export(export_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/exports/{export_id}/download")
def download_bulk_export(
    export_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("privacy.view")),
):
    svc = PrivacyService(db, actor)
    try:
        content, media_type, filename = svc.download_export(export_id)
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

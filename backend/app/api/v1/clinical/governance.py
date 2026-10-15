"""Clinical Governance API: Instrument catalog, configuration versions, and statutory approvals."""

from datetime import date
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_permission
from app.audit.service import audit
from app.services.clinical_governance import clinical_governance_service

router = APIRouter(prefix="/clinical/governance", tags=["Clinical Governance"])


class CreateVersionIn(BaseModel):
    source_reference: str = Field(..., max_length=255)
    schema_definition: dict[str, Any]
    effective_date: date
    review_date: date


class ApproveVersionIn(BaseModel):
    professional_designation: str = Field(..., max_length=150)  # e.g., "Consultant Psychiatrist / Medical Director"
    professional_registration: str = Field(..., max_length=100)  # e.g., "KMPDC Reg No. A12345"
    notes: Optional[str] = Field(default="", max_length=1000)


@router.get("/configurations")
def list_configurations(
    request: Request,
    facility_id: Optional[UUID] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("clinical.view")),
):
    target_facility_id = facility_id or actor.facility_id
    if not target_facility_id:
        raise HTTPException(status_code=400, detail="facility_id is required.")

    configs = clinical_governance_service.list_configurations(
        db, target_facility_id, category=category
    )
    audit(db, request, "clinical_governance.list_configurations", "clinical_governance", actor)
    return {
        "items": [
            {
                "id": str(c.id),
                "key": c.key,
                "name": c.name,
                "category": c.category,
                "description": c.description,
                "is_active": c.is_active,
                "current_version_id": str(c.current_version_id) if c.current_version_id else None,
                "versions_count": len(c.versions),
            }
            for c in configs
        ]
    }


@router.get("/configurations/{key}")
def get_configuration_details(
    key: str,
    request: Request,
    facility_id: Optional[UUID] = None,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("clinical.view")),
):
    target_facility_id = facility_id or actor.facility_id
    if not target_facility_id:
        raise HTTPException(status_code=400, detail="facility_id is required.")

    config = clinical_governance_service.get_configuration_by_key(db, target_facility_id, key)
    if not config:
        raise HTTPException(status_code=404, detail=f"Configuration for '{key}' not found.")

    audit(db, request, "clinical_governance.view_configuration", "clinical_governance", actor, config.id)
    return {
        "id": str(config.id),
        "key": config.key,
        "name": config.name,
        "category": config.category,
        "description": config.description,
        "is_active": config.is_active,
        "current_version_id": str(config.current_version_id) if config.current_version_id else None,
        "versions": [
            {
                "id": str(v.id),
                "version_number": v.version_number,
                "source_reference": v.source_reference,
                "schema_definition": v.schema_definition,
                "effective_date": v.effective_date.isoformat(),
                "review_date": v.review_date.isoformat(),
                "status": v.status,
                "created_by": str(v.created_by),
                "created_at": v.created_at.isoformat(),
                "approvals": [
                    {
                        "id": str(a.id),
                        "approver_name": a.approver_name,
                        "professional_designation": a.professional_designation,
                        "professional_registration": a.professional_registration,
                        "approval_date": a.approval_date.isoformat(),
                        "status": a.status,
                        "notes": a.notes,
                    }
                    for a in v.approvals
                ],
            }
            for v in config.versions
        ],
    }


@router.post("/configurations/{config_id}/versions")
def create_configuration_version(
    config_id: UUID,
    payload: CreateVersionIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("clinical.edit")),
):
    try:
        version = clinical_governance_service.create_draft_version(
            db=db,
            configuration_id=config_id,
            schema_definition=payload.schema_definition,
            source_reference=payload.source_reference,
            effective_date=payload.effective_date,
            review_date=payload.review_date,
            user_id=actor.id,
        )
        audit(db, request, "clinical_governance.create_version", "clinical_configuration_version", actor, version.id)
        return {"id": str(version.id), "version_number": version.version_number, "status": version.status}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/versions/{version_id}/submit")
def submit_version_for_approval(
    version_id: UUID,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("clinical.edit")),
):
    try:
        version = clinical_governance_service.submit_for_approval(db, version_id)
        audit(db, request, "clinical_governance.submit_for_approval", "clinical_configuration_version", actor, version.id)
        return {"id": str(version.id), "status": version.status}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/versions/{version_id}/approve")
def approve_version(
    version_id: UUID,
    payload: ApproveVersionIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("clinical.edit")),
):
    """
    Statutory approval endpoint. Requires Medical Director or clinical authority.
    Must provide legal professional registration (e.g. KMPDC).
    """
    try:
        approval = clinical_governance_service.approve_version(
            db=db,
            version_id=version_id,
            approver_id=actor.id,
            approver_name=getattr(actor, "full_name", str(actor.id)),
            professional_designation=payload.professional_designation,
            professional_registration=payload.professional_registration,
            notes=payload.notes or "",
        )
        audit(
            db,
            request,
            "clinical_governance.approve_version",
            "clinical_approval",
            actor,
            approval.id,
            after={
                "professional_registration": payload.professional_registration,
                "designation": payload.professional_designation,
            },
        )
        return {
            "status": "APPROVED",
            "approval_id": str(approval.id),
            "approval_date": approval.approval_date.isoformat(),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/seed-defaults")
def seed_default_configurations(
    request: Request,
    facility_id: Optional[UUID] = None,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("clinical.edit")),
):
    target_facility_id = facility_id or actor.facility_id
    if not target_facility_id:
        raise HTTPException(status_code=400, detail="facility_id is required.")

    count = clinical_governance_service.seed_baseline_configurations(
        db, target_facility_id, actor.id
    )
    audit(db, request, "clinical_governance.seed_defaults", "clinical_governance", actor)
    return {"seeded": count, "message": f"Successfully initialized {count} clinical instruments in PENDING_APPROVAL state."}

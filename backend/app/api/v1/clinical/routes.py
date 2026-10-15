"""Clinical, nursing and investigation APIs with distinct permission boundaries."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit.service import audit
from app.core.database import get_db
from app.core.permissions import require_permission
from app.models import clinical as models
from app.schemas import clinical as schemas
from app.schemas.care import care_paging
from app.services.clinical import ClinicalService, record_out

router = APIRouter(tags=["Clinical, nursing and investigations"])


def register_resource(
    path, model, schema, view_permission, create_permission, method=None, note_kind=None
):
    def records(
        request: Request,
        args=Depends(care_paging),
        admission_id: UUID | None = None,
        client_id: UUID | None = None,
        status: str | None = None,
        db: Session = Depends(get_db, scope="function"),
        actor=Depends(require_permission(view_permission)),
    ):
        service = ClinicalService(db, request, actor)
        filters = []
        if client_id:
            service.repo.client(client_id)
            filters.append(model.client_id == client_id)
        rows, meta = service.repo.page(
            model, **args, admission_id=admission_id, status=status, filters=filters
        )
        audit(db, request, "clinical.records_accessed", model.__tablename__, actor)
        items = [
            service.effective_note(row, note_kind)
            if note_kind
            else service.laboratory_out(row)
            if model is models.LaboratoryRequest
            else record_out(row)
            for row in rows
        ]
        return {"items": items, "meta": meta}

    records.__name__ = f"list_{model.__tablename__}"
    router.add_api_route(path, records, methods=["GET"])

    def create(
        data,
        request: Request,
        db: Session = Depends(get_db, scope="function"),
        actor=Depends(require_permission(create_permission)),
    ):
        service = ClinicalService(db, request, actor)
        return getattr(service, method)(data) if method else service.create_care(model, data)

    create.__annotations__["data"] = schema
    create.__name__ = f"create_{model.__tablename__}"
    router.add_api_route(path, create, methods=["POST"], status_code=201)


register_resource(
    "/clinical/encounters",
    models.ClinicalEncounter,
    schemas.EncounterIn,
    "clinical.view",
    "clinical.create_note",
    "create_encounter",
    "ENCOUNTER",
)
register_resource(
    "/clinical/problems",
    models.ClinicalProblem,
    schemas.ProblemIn,
    "clinical.view",
    "clinical.create_note",
    "create_problem",
)
register_resource(
    "/clinical/allergies",
    models.ClinicalAllergy,
    schemas.AllergyIn,
    "clinical.view",
    "clinical.create_note",
    "create_allergy",
)
register_resource(
    "/clinical/vitals",
    models.VitalSign,
    schemas.VitalsIn,
    "clinical.view",
    "clinical.record_vitals",
)
register_resource(
    "/clinical/orders",
    models.MedicalOrder,
    schemas.OrderIn,
    "clinical.view",
    "clinical.manage_orders",
)
register_resource(
    "/nursing/notes",
    models.NursingNote,
    schemas.NursingNoteIn,
    "nursing.view",
    "nursing.record",
    "create_nursing_note",
    "NURSING",
)
register_resource(
    "/nursing/observations",
    models.NursingObservation,
    schemas.ObservationIn,
    "nursing.view",
    "nursing.record",
)
register_resource(
    "/nursing/handovers",
    models.ShiftHandover,
    schemas.HandoverIn,
    "nursing.view",
    "nursing.record",
    "create_handover",
)
register_resource(
    "/lab/requests", models.LaboratoryRequest, schemas.LabRequestIn, "lab.view", "lab.order"
)
register_resource(
    "/toxicology/tests", models.ToxicologyTest, schemas.ToxicologyIn, "lab.view", "lab.result"
)


def register_revision(path, schema, model, kind, view, write):
    def correct(
        record_id: UUID,
        data,
        request: Request,
        db: Session = Depends(get_db, scope="function"),
        actor=Depends(require_permission(write)),
    ):
        return ClinicalService(db, request, actor).correct_note(record_id, data, kind)

    correct.__annotations__["data"] = schema
    correct.__name__ = f"revise_{model.__tablename__}"
    router.add_api_route(
        path + "/{record_id}/revisions", correct, methods=["POST"], status_code=201
    )

    def history(
        record_id: UUID,
        request: Request,
        db: Session = Depends(get_db, scope="function"),
        actor=Depends(require_permission(view)),
    ):
        service = ClinicalService(db, request, actor)
        service.repo.require(model, record_id)
        audit(db, request, "clinical.history_accessed", model.__tablename__, actor, record_id)
        return {"items": [record_out(row) for row in service.repo.revisions(kind, record_id)]}

    history.__name__ = f"history_{model.__tablename__}"
    router.add_api_route(path + "/{record_id}/revisions", history, methods=["GET"])


register_revision(
    "/clinical/encounters",
    schemas.EncounterRevisionIn,
    models.ClinicalEncounter,
    "ENCOUNTER",
    "clinical.view",
    "clinical.create_note",
)
register_revision(
    "/nursing/notes",
    schemas.NursingRevisionIn,
    models.NursingNote,
    "NURSING",
    "nursing.view",
    "nursing.record",
)


@router.patch("/clinical/problems/{record_id}")
def problem_status(
    record_id: UUID,
    data: schemas.ProblemUpdate,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("clinical.create_note")),
):
    return ClinicalService(db, request, actor).update_problem(record_id, data)


@router.patch("/clinical/allergies/{record_id}")
def allergy_status(
    record_id: UUID,
    data: schemas.AllergyUpdate,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("clinical.create_note")),
):
    return ClinicalService(db, request, actor).update_allergy(record_id, data)


@router.patch("/clinical/orders/{record_id}")
def close_order(
    record_id: UUID,
    data: schemas.OrderUpdate,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("clinical.manage_orders")),
):
    return ClinicalService(db, request, actor).complete_order(record_id, data)


@router.post("/nursing/handovers/{record_id}/acknowledge")
def acknowledge_handover(
    record_id: UUID,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("nursing.record")),
):
    return ClinicalService(db, request, actor).acknowledge_handover(record_id)


@router.get("/nursing/dashboard")
def nursing_dashboard(
    request: Request,
    args=Depends(care_paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("nursing.view")),
):
    return ClinicalService(db, request, actor).nursing_dashboard(args["page"], args["page_size"])


@router.post("/lab/requests/{record_id}/results", status_code=201)
def lab_result(
    record_id: UUID,
    data: schemas.LabResultIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("lab.result")),
):
    return ClinicalService(db, request, actor).add_lab_result(record_id, data)


@router.post("/lab/results/{record_id}/review")
def review_result(
    record_id: UUID,
    data: schemas.LabReviewIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("clinical.manage_orders")),
):
    return ClinicalService(db, request, actor).review_lab_result(record_id, data)


@router.post("/lab/requests/{record_id}/attachments", status_code=201)
def upload_pdf(
    record_id: UUID,
    data: schemas.PdfAttachmentIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("lab.result")),
):
    return ClinicalService(db, request, actor).attach_pdf(record_id, data)


@router.get("/lab/attachments/{record_id}")
def download_pdf(
    record_id: UUID,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("lab.view")),
):
    service = ClinicalService(db, request, actor)
    attachment = service.repo.require(models.LaboratoryAttachment, record_id)
    audit(db, request, "document.accessed", "laboratory_attachment", actor, attachment.id)
    return Response(
        attachment.content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{attachment.filename}"',
            "Content-Security-Policy": "sandbox",
        },
    )


@router.get("/toxicology/trends")
def toxicology_trends(
    request: Request,
    admission_id: UUID,
    args=Depends(care_paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("lab.view")),
):
    service = ClinicalService(db, request, actor)
    rows, meta = service.repo.page(models.ToxicologyTest, **args, admission_id=admission_id)
    audit(db, request, "toxicology.trends_accessed", "admission", actor, admission_id)
    return {
        "items": [{"id": row.id, "test_at": row.test_at, "results": row.results} for row in rows],
        "meta": meta,
    }


class CrisisReviewIn(BaseModel):
    response: str
    intervention: str


class CrisisResolveIn(BaseModel):
    resolution: str


class CrisisScanIn(BaseModel):
    text: str
    client_id: Optional[UUID] = None
    admission_id: Optional[UUID] = None
    source_entity: str = "ClinicalNote"
    source_entity_id: str = "Unknown"


@router.get("/crisis-alerts")
def crisis_alerts(
    request: Request,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    args=Depends(care_paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("clinical.view")),
):
    from app.audit.service import audit
    from sqlalchemy import select
    from app.models.clinical import CrisisAlert

    query = select(CrisisAlert).filter(CrisisAlert.facility_id == actor.facility_id)
    if status:
        query = query.filter(CrisisAlert.status == status)
    else:
        # Default: non-resolved
        query = query.filter(CrisisAlert.status.in_(["NEW", "ESCALATED", "DETECTED", "ACKNOWLEDGED", "UNDER_REVIEW"]))

    if severity:
        query = query.filter(CrisisAlert.severity == severity)

    query = query.order_by(CrisisAlert.created_at.desc())
    items = list(db.scalars(query.offset(args.get("offset", 0)).limit(args.get("limit", 50))).all())
    total = len(items)

    audit(db, request, "clinical.crisis_alerts_accessed", "crisis_alert", actor)
    return {
        "items": [
            {
                "id": str(r.id),
                "alert_reference": r.alert_reference,
                "client_id": str(r.client_id) if r.client_id else None,
                "admission_id": str(r.admission_id) if r.admission_id else None,
                "trigger": r.trigger,
                "severity": r.severity,
                "status": r.status,
                "detected_keywords": r.detected_keywords,
                "text_snippet": r.text_snippet,
                "assigned_clinician_id": str(r.assigned_clinician_id) if r.assigned_clinician_id else None,
                "acknowledged_by": str(r.acknowledged_by) if r.acknowledged_by else None,
                "acknowledged_at": r.acknowledged_at.isoformat() if r.acknowledged_at else None,
                "response": r.response,
                "intervention": r.intervention,
                "resolution": r.resolution,
                "resolved_by_id": str(r.resolved_by_id) if r.resolved_by_id else None,
                "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
                "escalation_level": r.escalation_level,
                "escalation_history": r.escalation_history or [],
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in items
        ],
        "meta": {"limit": args.get("limit", 50), "offset": args.get("offset", 0), "total": total},
    }


@router.post("/crisis-alerts/{record_id}/acknowledge")
def acknowledge_crisis_alert(
    record_id: UUID,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("clinical.create_note")),
):
    from app.services.crisis import crisis_escalation_service
    from app.audit.service import audit

    try:
        alert = crisis_escalation_service.acknowledge_alert(
            db=db, alert_id=record_id, user_id=actor.id, note="Acknowledged via clinical dashboard"
        )
        audit(db, request, "clinical.crisis_alert_acknowledged", "crisis_alert", actor, record_id)
        return {"id": str(alert.id), "status": alert.status, "alert_reference": alert.alert_reference}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/crisis-alerts/{record_id}/review")
def review_crisis_alert(
    record_id: UUID,
    payload: CrisisReviewIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("clinical.create_note")),
):
    from app.services.crisis import crisis_escalation_service
    from app.audit.service import audit

    try:
        alert = crisis_escalation_service.start_review(
            db=db,
            alert_id=record_id,
            user_id=actor.id,
            response_summary=payload.response,
            intervention_plan=payload.intervention,
        )
        audit(db, request, "clinical.crisis_alert_reviewed", "crisis_alert", actor, record_id)
        return {"id": str(alert.id), "status": alert.status, "alert_reference": alert.alert_reference}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/crisis-alerts/{record_id}/resolve")
def resolve_crisis_alert(
    record_id: UUID,
    payload: CrisisResolveIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("clinical.create_note")),
):
    from app.services.crisis import crisis_escalation_service
    from app.audit.service import audit

    try:
        alert = crisis_escalation_service.resolve_alert(
            db=db, alert_id=record_id, user_id=actor.id, resolution_notes=payload.resolution
        )
        audit(db, request, "clinical.crisis_alert_resolved", "crisis_alert", actor, record_id)
        return {"id": str(alert.id), "status": alert.status, "alert_reference": alert.alert_reference}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/crisis-alerts/scan-text")
def scan_text_for_crisis_alerts(
    payload: CrisisScanIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("clinical.view")),
):
    from app.services.crisis import scan_text_for_crisis

    matches = scan_text_for_crisis(
        text=payload.text,
        db=db,
        facility_id=actor.facility_id,
        client_id=payload.client_id,
        admission_id=payload.admission_id,
        source_entity=payload.source_entity,
        source_entity_id=payload.source_entity_id,
        assigned_clinician_id=actor.id,
    )
    db.commit()
    return {"matches": matches, "count": len(matches)}


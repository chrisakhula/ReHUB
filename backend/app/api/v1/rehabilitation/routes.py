from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models import rehabilitation as models
from app.schemas import rehabilitation as schemas
from app.services.rehabilitation import RehabilitationService, record_out

router = APIRouter(prefix="/rehabilitation", tags=["Assessments and rehabilitation"])


@router.get("/assessment-types")
def assessment_types(
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("assessment.view")),
):
    from sqlalchemy import select

    from app.models.assessment_types import AssessmentType

    return {
        "items": [
            record_out(row)
            for row in db.scalars(select(AssessmentType).order_by(AssessmentType.name))
        ]
    }


def paging(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str = Query("", max_length=100),
    sort: str = "created_at",
    direction: str = Query("desc", pattern="^(asc|desc)$"),
    start: date | None = None,
    end: date | None = None,
    admission_id: UUID | None = None,
    status: str | None = None,
    current_only: bool = True,
    root_id: UUID | None = None,
):
    from datetime import datetime, time, timedelta

    from app.core.time import EAT

    return {
        "page": page,
        "page_size": page_size,
        "q": q,
        "sort": sort,
        "direction": direction,
        "start": datetime.combine(start, time.min, EAT) if start else None,
        "end": datetime.combine(end + timedelta(days=1), time.min, EAT) if end else None,
        "admission_id": admission_id,
        "status": status,
        "current_only": current_only,
        "root_id": root_id,
    }


def register_resource(path, model, schema, read, write, method):
    def records(
        request: Request,
        args=Depends(paging),
        db: Session = Depends(get_db, scope="function"),
        actor=Depends(require_permission(read)),
    ):
        return RehabilitationService(db, request, actor).list(model, args)

    records.__name__ = f"list_{model.__tablename__}"
    router.add_api_route(path, records, methods=["GET"])

    def get_record(
        record_id: UUID,
        request: Request,
        db: Session = Depends(get_db, scope="function"),
        actor=Depends(require_permission(read)),
    ):
        return RehabilitationService(db, request, actor).get(model, record_id)

    get_record.__name__ = f"get_{model.__tablename__}"
    router.add_api_route(path + "/{record_id}", get_record, methods=["GET"])

    def create(
        data,
        request: Request,
        db: Session = Depends(get_db, scope="function"),
        actor=Depends(require_permission(write)),
    ):
        return record_out(getattr(RehabilitationService(db, request, actor), method)(data))

    create.__annotations__["data"] = schema
    create.__name__ = f"create_{model.__tablename__}"
    router.add_api_route(path, create, methods=["POST"], status_code=201)


@router.get("/risk-alerts")
def risk_alerts(
    request: Request,
    args=Depends(paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("risk.view")),
):
    return RehabilitationService(db, request, actor).list(
        models.RiskAssessment,
        args,
        extra=(
            models.RiskAssessment.level.in_(["HIGH", "CRITICAL"]),
            models.RiskAssessment.status == "ACTIVE",
        ),
    )


@router.get("/case-dashboard")
def case_dashboard(
    request: Request,
    args=Depends(paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("case_management.view")),
):
    return RehabilitationService(db, request, actor).case_dashboard(args)


@router.get("/programme/schedule")
def programme_schedule(
    request: Request,
    from_date: date,
    to_date: date,
    args=Depends(paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("programme.view")),
):
    return RehabilitationService(db, request, actor).schedule(from_date, to_date, args)


register_resource(
    "/substances",
    models.Substance,
    schemas.SubstanceIn,
    "assessment.view",
    "assessment.configure",
    "substance",
)
register_resource(
    "/substance-histories",
    models.SubstanceHistory,
    schemas.SubstanceHistoryIn,
    "assessment.view",
    "assessment.record",
    "substance_history",
)
register_resource(
    "/instruments",
    models.AssessmentInstrument,
    schemas.InstrumentIn,
    "assessment.view",
    "assessment.configure",
    "instrument",
)
register_resource(
    "/scores",
    models.InstrumentAssessment,
    schemas.InstrumentAssessmentIn,
    "assessment.view",
    "assessment.record",
    "score",
)
register_resource(
    "/biopsychosocial",
    models.BiopsychosocialAssessment,
    schemas.BiopsychosocialIn,
    "assessment.view",
    "assessment.record",
    "biopsychosocial",
)
register_resource(
    "/risks", models.RiskAssessment, schemas.RiskIn, "risk.view", "risk.record", "risk"
)
register_resource(
    "/treatment-plans",
    models.TreatmentPlan,
    schemas.TreatmentPlanIn,
    "treatment_plan.view",
    "treatment_plan.manage",
    "treatment_plan",
)
register_resource(
    "/cases",
    models.CaseAssignment,
    schemas.CaseAssignmentIn,
    "case_management.view",
    "treatment_plan.manage",
    "case",
)
register_resource(
    "/sessions",
    models.TherapySession,
    schemas.TherapySessionIn,
    "therapy.view",
    "therapy.create_note",
    "therapy",
)
register_resource(
    "/groups",
    models.GroupSession,
    schemas.GroupSessionIn,
    "therapy.view",
    "therapy.create_note",
    "group",
)
register_resource(
    "/programme",
    models.ProgrammeActivity,
    schemas.ProgrammeActivityIn,
    "programme.view",
    "programme.manage",
    "programme",
)
register_resource(
    "/family-communications",
    models.FamilyCommunication,
    schemas.FamilyCommunicationIn,
    "family.view",
    "family.record",
    "family",
)


@router.post("/groups/{record_id}/attendance", status_code=201)
def group_attendance(
    record_id: UUID,
    data: schemas.GroupAttendanceIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("therapy.create_note")),
):
    return record_out(
        RehabilitationService(db, request, actor).group_attendance(record_id, data), private=True
    )


@router.get("/groups/{record_id}/attendance")
def group_attendance_list(
    record_id: UUID,
    request: Request,
    args=Depends(paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("therapy.view")),
):
    service = RehabilitationService(db, request, actor)
    service.repo.require(models.GroupSession, record_id)
    return service.list(
        models.GroupAttendance, args, extra=(models.GroupAttendance.group_session_id == record_id,)
    )


@router.post("/programme/{record_id}/attendance", status_code=201)
def programme_attendance(
    record_id: UUID,
    data: schemas.ProgrammeAttendanceIn,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("programme.manage")),
):
    return record_out(
        RehabilitationService(db, request, actor).programme_attendance(record_id, data)
    )


@router.get("/programme/{record_id}/attendance")
def programme_attendance_list(
    record_id: UUID,
    request: Request,
    args=Depends(paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("programme.view")),
):
    service = RehabilitationService(db, request, actor)
    service.repo.require(models.ProgrammeActivity, record_id)
    return service.list(
        models.ProgrammeAttendance,
        args,
        extra=(models.ProgrammeAttendance.activity_id == record_id,),
    )


@router.get("/score-trends")
def score_trends(
    request: Request,
    admission_id: UUID,
    instrument_code: str | None = None,
    instrument_id: UUID | None = None,
    args=Depends(paging),
    db: Session = Depends(get_db, scope="function"),
    actor=Depends(require_permission("assessment.view")),
):
    from sqlalchemy import select

    service = RehabilitationService(db, request, actor)
    args["admission_id"] = admission_id
    extra = (
        (
            models.InstrumentAssessment.instrument_id.in_(
                select(models.AssessmentInstrument.id).where(
                    models.AssessmentInstrument.code == instrument_code
                )
            ),
        )
        if instrument_code
        else ()
    )
    if instrument_id:
        service.repo.require(models.AssessmentInstrument, instrument_id)
        extra += (models.InstrumentAssessment.instrument_id == instrument_id,)
    return service.list(models.InstrumentAssessment, args, extra=extra)

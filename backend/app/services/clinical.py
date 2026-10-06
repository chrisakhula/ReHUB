import base64
import binascii
import hashlib
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import func, select

from app.audit.service import audit
from app.core.permissions import aware
from app.core.security import permission_codes
from app.models.clinical import (
    ClinicalAllergy,
    ClinicalEncounter,
    ClinicalProblem,
    ClinicalRevision,
    LaboratoryAttachment,
    LaboratoryRequest,
    LaboratoryResult,
    MedicalOrder,
    NursingNote,
    NursingObservation,
    ShiftHandover,
    ToxicologyTest,
)
from app.models.identity import utcnow
from app.repositories.clinical import ClinicalRepository


def record_out(record):
    return {
        column.key: getattr(record, column.key)
        for column in record.__table__.columns
        if column.key != "content"
    }


class ClinicalService:
    def __init__(self, db, request, actor):
        self.db, self.request, self.actor = db, request, actor
        self.repo = ClinicalRepository(db, actor)

    def event(self, action, row, previous=None, new=None, reason=None):
        audit(
            self.db,
            self.request,
            action,
            row.__tablename__,
            self.actor,
            row.id,
            previous=previous,
            new=new,
            reason=reason,
        )

    def add(self, model, values):
        row = model(
            **values,
            facility_id=self.actor.facility_id,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(row)
        self.db.flush()
        self.event(
            "clinical.created", row, new={"admission_id": str(getattr(row, "admission_id", ""))}
        )
        return row

    def admission_values(self, data):
        values = data.model_dump()
        admission = self.repo.admission(data.admission_id)
        for key in ("encounter_at", "noted_at", "observed_at", "test_at"):
            when = values.get(key)
            if when and (aware(when) < aware(admission.admission_date) or aware(when) > utcnow()):
                raise HTTPException(
                    422, "Care time must be during the admission and cannot be future dated"
                )
        values["client_id"] = admission.client_id
        return values

    def clinician(self, staff_id):
        clinician = self.repo.staff(staff_id or self.actor.id)
        if "clinical.create_note" not in permission_codes(clinician):
            raise HTTPException(422, "Responsible clinician must have clinical note permission")
        return clinician.id

    def encounter_link(self, encounter_id, admission_id):
        if encounter_id:
            encounter = self.repo.require(ClinicalEncounter, encounter_id)
            if encounter.admission_id != admission_id:
                raise HTTPException(422, "Encounter belongs to a different admission")

    def initial_revision(self, row, kind, snapshot):
        revision = ClinicalRevision(
            facility_id=self.actor.facility_id,
            entity_type=kind,
            entity_id=row.id,
            version=1,
            snapshot=snapshot,
            reason="Original record",
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(revision)
        self.db.flush()

    def effective_note(self, row, kind):
        revisions = self.repo.revisions(kind, row.id)
        output = record_out(row)
        if revisions:
            output.update(revisions[-1].snapshot)
            output["version"] = revisions[-1].version
            output["last_corrected_at"] = revisions[-1].created_at
            output["last_corrected_by"] = revisions[-1].created_by
        return output

    def create_encounter(self, data):
        values = self.admission_values(data)
        values["clinician_id"] = self.clinician(data.clinician_id)
        row = self.add(ClinicalEncounter, values)
        snapshot = data.model_dump(mode="json")
        snapshot["clinician_id"] = str(values["clinician_id"])
        self.initial_revision(row, "ENCOUNTER", snapshot)
        return self.effective_note(row, "ENCOUNTER")

    def create_nursing_note(self, data):
        values = self.admission_values(data)
        if data.escalated_to_id:
            self.repo.staff(data.escalated_to_id)
        row = self.add(NursingNote, values)
        self.initial_revision(row, "NURSING", data.model_dump(mode="json"))
        return self.effective_note(row, "NURSING")

    def correct_note(self, record_id, data, kind):
        model = ClinicalEncounter if kind == "ENCOUNTER" else NursingNote
        row = self.repo.require(model, record_id, lock=True)
        if row.admission_id != data.admission_id:
            raise HTTPException(422, "A correction cannot change the admission")
        self.repo.admission(row.admission_id, writable=False)
        revisions = self.repo.revisions(kind, row.id)
        version = revisions[-1].version
        if version != data.expected_version:
            raise HTTPException(409, "This record has changed; reload before correcting it")
        snapshot = data.model_dump(mode="json", exclude={"reason", "expected_version"})
        if kind == "ENCOUNTER":
            snapshot["clinician_id"] = str(self.clinician(data.clinician_id))
        elif data.escalated_to_id:
            self.repo.staff(data.escalated_to_id)
        self.db.add(
            ClinicalRevision(
                facility_id=self.actor.facility_id,
                entity_type=kind,
                entity_id=row.id,
                version=version + 1,
                snapshot=snapshot,
                reason=data.reason,
                created_by=self.actor.id,
                updated_by=self.actor.id,
            )
        )
        self.event(
            "clinical.note_corrected",
            row,
            previous={"version": version},
            new={"version": version + 1},
            reason=data.reason,
        )
        self.db.flush()
        return self.effective_note(row, kind)

    def create_problem(self, data):
        self.repo.client(data.client_id)
        if data.admission_id:
            admission = self.repo.admission(data.admission_id)
            if admission.client_id != data.client_id:
                raise HTTPException(422, "Admission belongs to a different client")
        return record_out(self.add(ClinicalProblem, data.model_dump()))

    def update_problem(self, record_id, data):
        row = self.repo.require(ClinicalProblem, record_id, lock=True)
        previous = row.status
        row.status, row.resolution = data.status, data.resolution
        row.resolved_at = utcnow() if data.status == "RESOLVED" else None
        row.updated_by = self.actor.id
        self.event(
            "clinical.problem_status_changed",
            row,
            previous={"status": previous},
            new={"status": row.status},
            reason=data.reason,
        )
        return record_out(row)

    def create_allergy(self, data):
        client = self.repo.client(data.client_id, lock=True)
        existing = self.db.scalar(
            select(ClinicalAllergy).where(
                ClinicalAllergy.facility_id == self.actor.facility_id,
                ClinicalAllergy.client_id == client.id,
                ClinicalAllergy.substance.ilike(data.substance),
                ClinicalAllergy.status == "ACTIVE",
            )
        )
        if existing:
            raise HTTPException(409, "This active allergy is already recorded")
        row = self.add(ClinicalAllergy, data.model_dump())
        client.allergies = list(dict.fromkeys([*(client.allergies or []), data.substance]))
        client.updated_by = self.actor.id
        return record_out(row)

    def update_allergy(self, record_id, data):
        row = self.repo.require(ClinicalAllergy, record_id, lock=True)
        client = self.repo.client(row.client_id, lock=True)
        previous = row.status
        row.status, row.updated_by = data.status, self.actor.id
        self.db.flush()
        other_active = self.db.scalar(
            select(ClinicalAllergy.id).where(
                ClinicalAllergy.facility_id == self.actor.facility_id,
                ClinicalAllergy.client_id == client.id,
                ClinicalAllergy.id != row.id,
                ClinicalAllergy.substance.ilike(row.substance),
                ClinicalAllergy.status == "ACTIVE",
            )
        )
        if data.status == "ACTIVE":
            client.allergies = list(dict.fromkeys([*(client.allergies or []), row.substance]))
        elif not other_active:
            client.allergies = [
                s for s in (client.allergies or []) if str(s).casefold() != row.substance.casefold()
            ]
        client.updated_by = self.actor.id
        self.event(
            "clinical.allergy_status_changed",
            row,
            previous={"status": previous},
            new={"status": row.status},
            reason=data.reason,
        )
        return record_out(row)

    def create_care(self, model, data):
        values = self.admission_values(data)
        if "encounter_id" in values:
            self.encounter_link(values["encounter_id"], data.admission_id)
        if model == ToxicologyTest:
            staff = self.repo.staff(data.staff_id or self.actor.id)
            if not {"lab.result", "nursing.record", "clinical.create_note"}.intersection(
                permission_codes(staff)
            ):
                raise HTTPException(
                    422, "Testing staff must have a clinical, nursing or result permission"
                )
            values["staff_id"] = staff.id
            values["results"] = [r.model_dump() for r in data.results]
        return record_out(self.add(model, values))

    def complete_order(self, record_id, data):
        row = self.repo.require(MedicalOrder, record_id, lock=True)
        if row.status != "PENDING":
            raise HTTPException(409, "Order is already completed or cancelled")
        row.status, row.completion_note = data.status, data.completion_note
        row.completed_at, row.updated_by = utcnow(), self.actor.id
        self.event("clinical.order_closed", row, new={"status": row.status}, reason=data.reason)
        return record_out(row)

    def create_handover(self, data):
        if data.admission_id:
            self.repo.admission(data.admission_id)
        return record_out(self.add(ShiftHandover, data.model_dump()))

    def acknowledge_handover(self, record_id):
        row = self.repo.require(ShiftHandover, record_id, lock=True)
        if row.acknowledged_at:
            raise HTTPException(409, "Handover has already been acknowledged")
        row.acknowledged_by, row.acknowledged_at = self.actor.id, utcnow()
        row.updated_by = self.actor.id
        self.event("nursing.handover_acknowledged", row)
        return record_out(row)

    def laboratory_out(self, row):
        output = record_out(row)
        output["results"] = [record_out(result) for result in self.repo.results(row.id)]
        output["attachments"] = self.repo.attachments(row.id)
        return output

    def add_lab_result(self, record_id, data):
        row = self.repo.require(LaboratoryRequest, record_id, lock=True)
        if aware(data.resulted_at) > utcnow():
            raise HTTPException(422, "Result date cannot be in the future")
        previous = self.repo.results(row.id)
        if previous and len(data.correction_reason.strip()) < 3:
            raise HTTPException(422, "A reason is required for a corrected laboratory result")
        if row.specimen_at and data.resulted_at < row.specimen_at:
            raise HTTPException(422, "A result cannot precede specimen collection")
        result = self.add(LaboratoryResult, {**data.model_dump(), "request_id": row.id})
        row.status, row.updated_by = "RESULTED", self.actor.id
        self.event(
            "laboratory.result_recorded",
            result,
            new={"request_id": str(row.id)},
            reason=data.correction_reason or None,
        )
        return self.laboratory_out(row)

    def review_lab_result(self, result_id, data):
        result = self.repo.require(LaboratoryResult, result_id, lock=True)
        row = self.repo.require(LaboratoryRequest, result.request_id, lock=True)
        if result.reviewed_at:
            raise HTTPException(409, "This result has already been reviewed")
        latest = self.repo.results(row.id)[-1]
        if latest.id != result.id:
            raise HTTPException(409, "Review the current laboratory result")
        result.reviewed_at, result.reviewed_by = utcnow(), self.actor.id
        result.review_note, result.updated_by = data.review_note, self.actor.id
        row.status, row.updated_by = "REVIEWED", self.actor.id
        self.event("laboratory.result_reviewed", result, new={"request_id": str(row.id)})
        return self.laboratory_out(row)

    def attach_pdf(self, record_id, data):
        row = self.repo.require(LaboratoryRequest, record_id)
        try:
            content = base64.b64decode(data.content_base64, validate=True)
        except (ValueError, binascii.Error):
            raise HTTPException(422, "Invalid PDF encoding") from None
        from app.services.file_validation import validate_pdf

        content = validate_pdf(content)
        attachment = self.add(
            LaboratoryAttachment,
            {
                "request_id": row.id,
                "filename": data.filename,
                "content": content,
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            },
        )
        return record_out(attachment)

    def nursing_dashboard(self, page=1, page_size=20):
        from app.models.clients import Admission

        active_statuses = {"ACTIVE", "ON_LEAVE", "HOSPITALIZED", "AWOL", "DISCHARGE_PENDING"}
        total = self.db.scalar(
            select(func.count())
            .select_from(Admission)
            .where(
                Admission.facility_id == self.actor.facility_id,
                Admission.status.in_(active_statuses),
            )
        )
        admissions = list(
            self.db.scalars(
                select(Admission)
                .where(
                    Admission.facility_id == self.actor.facility_id,
                    Admission.status.in_(active_statuses),
                )
                .order_by(Admission.admission_date.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        now = utcnow()
        residents, outside = [], []
        for admission in admissions:
            client = self.repo.client(admission.client_id)
            note = self.db.scalar(
                select(NursingNote)
                .where(
                    NursingNote.facility_id == self.actor.facility_id,
                    NursingNote.admission_id == admission.id,
                )
                .order_by(NursingNote.noted_at.desc(), NursingNote.created_at.desc())
                .limit(1)
            )
            observation = self.db.scalar(
                select(NursingObservation)
                .where(
                    NursingObservation.facility_id == self.actor.facility_id,
                    NursingObservation.admission_id == admission.id,
                )
                .order_by(
                    NursingObservation.observed_at.desc(), NursingObservation.created_at.desc()
                )
                .limit(1)
            )
            effective_note = self.effective_note(note, "NURSING") if note else None
            due = observation.next_observation_at if observation else None
            if effective_note and effective_note.get("observation_due_at"):
                from datetime import datetime

                note_due = datetime.fromisoformat(
                    effective_note["observation_due_at"].replace("Z", "+00:00")
                )
                if not observation or note.noted_at > observation.observed_at:
                    due = note_due
            high_risk = bool(effective_note and effective_note.get("high_risk"))
            if "risk.view" in permission_codes(self.actor):
                from app.models.rehabilitation import RiskAssessment

                newer = select(RiskAssessment.supersedes_id).where(
                    RiskAssessment.supersedes_id.is_not(None)
                )
                high_risk = high_risk or bool(
                    self.db.scalar(
                        select(RiskAssessment.id)
                        .where(
                            RiskAssessment.facility_id == self.actor.facility_id,
                            RiskAssessment.admission_id == admission.id,
                            RiskAssessment.status == "ACTIVE",
                            RiskAssessment.level.in_(["HIGH", "CRITICAL"]),
                            RiskAssessment.id.not_in(newer),
                        )
                        .limit(1)
                    )
                )
            item = {
                "initial_risk_flags": admission.risk_flags,
                "admission_id": admission.id,
                "admission_number": admission.admission_number,
                "client_id": client.id,
                "client_number": client.client_number,
                "client_name": " ".join(
                    filter(None, [client.first_name, client.middle_name, client.surname])
                ),
                "status": admission.status,
                "admission_date": admission.admission_date,
                "high_risk": high_risk,
                "observation_due_at": due,
                "observation_due": bool(due and due <= now),
            }
            residents.append(item)
            if admission.status in {"ON_LEAVE", "HOSPITALIZED", "AWOL"}:
                outside.append(item)
        handovers = list(
            self.db.scalars(
                select(ShiftHandover)
                .where(
                    ShiftHandover.facility_id == self.actor.facility_id,
                    ShiftHandover.acknowledged_at.is_(None),
                )
                .order_by(ShiftHandover.created_at.desc())
                .limit(20)
            )
        )
        audit(self.db, self.request, "nursing.dashboard_accessed", "nursing_dashboard", self.actor)
        return {
            "meta": {"page": page, "page_size": page_size, "total": total},
            "residents": residents,
            "high_risk": [r for r in residents if r["high_risk"]],
            "observations_due": [r for r in residents if r["observation_due"]],
            "new_admissions": [
                r for r in residents if r["admission_date"] >= now - timedelta(hours=24)
            ],
            "outside_facility": outside,
            "handovers": [record_out(r) for r in handovers],
            "incidents": None,
            "incidents_available": False,
            "medication_due_endpoint": "/api/v1/medication/due",
        }

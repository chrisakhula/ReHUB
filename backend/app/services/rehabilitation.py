"""Clinical validation and privacy controls; routes only orchestrate these operations."""

from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.inspection import inspect

from app.audit.service import audit
from app.core.permissions import aware
from app.core.security import permission_codes
from app.core.time import EAT, business_today
from app.models.identity import utcnow
from app.models.rehabilitation import (
    AssessmentInstrument,
    BiopsychosocialAssessment,
    CaseAssignment,
    FamilyCommunication,
    GroupAttendance,
    GroupSession,
    InstrumentAssessment,
    ProgrammeActivity,
    ProgrammeAttendance,
    RiskAssessment,
    Substance,
    SubstanceHistory,
    TherapySession,
    TreatmentPlan,
)
from app.repositories.rehabilitation import RehabilitationRepository


def record_out(record, private=True):
    result = {
        attribute.key: getattr(record, attribute.key)
        for attribute in inspect(type(record)).column_attrs
    }
    if not private:
        result.pop("private_observation", None)
    return result


class RehabilitationService:
    def __init__(self, db, request, actor):
        self.db, self.request, self.actor = db, request, actor
        self.repo = RehabilitationRepository(db, actor)

    def allowed(self, permission):
        if permission not in permission_codes(self.actor):
            raise HTTPException(403, "You do not have permission for this action")

    def access(self, entity, record_id=None):
        audit(self.db, self.request, f"{entity}.accessed", entity, self.actor, record_id)

    def save(self, model, values):
        row = model(
            **values,
            facility_id=self.actor.facility_id,
            created_by=self.actor.id,
            updated_by=self.actor.id,
        )
        self.db.add(row)
        self.db.flush()
        # Audit events contain record links and state, never clinical narrative.
        safe = {
            key: str(getattr(row, key))
            for key in ("admission_id", "status", "version", "supersedes_id")
            if getattr(row, key, None) is not None
        }
        audit(
            self.db,
            self.request,
            f"{model.__tablename__}.created",
            model.__tablename__,
            self.actor,
            row.id,
            new=safe,
        )
        return row

    def revision(self, model, data):
        admission = self.repo.admission(data.admission_id, writable=not bool(data.supersedes_id))
        previous = None
        if data.supersedes_id:
            previous = self.repo.require(model, data.supersedes_id, lock=True)
            if previous.admission_id != admission.id:
                raise HTTPException(422, "A revision must belong to the same admission")
            if self.db.scalar(select(model.id).where(model.supersedes_id == previous.id)):
                raise HTTPException(
                    409, "This record has already been revised; revise its latest version"
                )
        return admission, previous

    def list(self, model, args, extra=()):
        rows, meta = self.repo.page_records(model, **args, extra=extra)
        self.access(model.__tablename__)
        private = "psychotherapy.view" in permission_codes(self.actor)
        return {"items": [record_out(row, private=private) for row in rows], "meta": meta}

    def get(self, model, record_id):
        row = self.repo.require(model, record_id)
        self.access(model.__tablename__, row.id)
        return record_out(row, private="psychotherapy.view" in permission_codes(self.actor))

    def substance(self, data):
        if self.db.scalar(
            select(Substance).where(
                Substance.facility_id == self.actor.facility_id, Substance.name == data.name
            )
        ):
            raise HTTPException(409, "A substance with this name already exists")
        return self.save(Substance, data.model_dump())

    def substance_history(self, data):
        admission, previous = self.revision(SubstanceHistory, data)
        substance = self.repo.require(Substance, data.substance_id)
        if not substance.active:
            raise HTTPException(422, "Select an active substance")
        if previous and previous.substance_id != data.substance_id:
            raise HTTPException(422, "A revision cannot change the substance")
        if data.last_use and aware(data.last_use) > utcnow():
            raise HTTPException(422, "Last use cannot be in the future")
        client = self.repo.client(admission.client_id)
        if client.date_of_birth and data.first_use_age is not None:
            age = (business_today() - client.date_of_birth).days // 365
            if data.first_use_age > age or (
                data.regular_use_age is not None and data.regular_use_age > age
            ):
                raise HTTPException(422, "Use ages cannot exceed the client's age")
        return self.save(SubstanceHistory, data.model_dump())

    def instrument(self, data):
        # A changed configuration is always a new version; historical scores keep their tool.
        from app.models.identity import Facility

        self.db.scalar(
            select(Facility).where(Facility.id == self.actor.facility_id).with_for_update()
        )
        return self.save(
            AssessmentInstrument,
            {**data.model_dump(mode="json"), "version": self.repo.instrument_version(data.code)},
        )

    def score(self, data):
        admission = self.repo.admission(data.admission_id)
        if aware(data.completed_at) < aware(admission.admission_date):
            raise HTTPException(422, "Assessment cannot precede admission")
        instrument = self.repo.require(AssessmentInstrument, data.instrument_id)
        if not instrument.active:
            raise HTTPException(422, "This instrument version is inactive")
        if aware(data.completed_at) > utcnow():
            raise HTTPException(422, "Assessment completion cannot be in the future")
        if set(data.responses) != {q["key"] for q in instrument.questions}:
            raise HTTPException(422, "Answer every question and include no unknown questions")
        score, domains, alert = 0, {}, False
        for question in instrument.questions:
            answer = data.responses[question["key"]]
            option = next((o for o in question["options"] if o["value"] == answer), None)
            if not option:
                raise HTTPException(422, "An assessment response is not a valid option")
            if question.get("contributes_to_score", True):
                score += option["score"]
                if question.get("domain"):
                    domains[question["domain"]] = (
                        domains.get(question["domain"], 0) + option["score"]
                    )
            if answer in question.get("alert_values", []):
                alert = True
        band = next(
            (
                b
                for b in instrument.score_bands
                if not b.get("domain") and b["minimum"] <= score <= b["maximum"]
            ),
            None,
        )
        if not band:
            raise HTTPException(422, "Instrument scoring configuration does not cover this score")
        for domain, value in list(domains.items()):
            domain_band = next(
                (
                    b
                    for b in instrument.score_bands
                    if b.get("domain") == domain and b["minimum"] <= value <= b["maximum"]
                ),
                None,
            )
            domains[domain] = (
                {
                    "score": value,
                    "interpretation": domain_band["interpretation"],
                    "risk_level": domain_band["risk_level"],
                }
                if domain_band
                else {"score": value}
            )
        levels = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}
        risk_level = max(
            [
                band["risk_level"],
                *[d.get("risk_level", "LOW") for d in domains.values()],
                "HIGH" if alert else "LOW",
            ],
            key=levels.get,
        )
        row = self.save(
            InstrumentAssessment,
            {
                **data.model_dump(),
                "score": score,
                "domain_scores": domains,
                "interpretation": band["interpretation"],
                "risk_level": risk_level,
                "completed_by": self.actor.id,
            },
        )
        if risk_level in {"HIGH", "CRITICAL"}:
            audit(
                self.db,
                self.request,
                "assessment.risk_alert",
                "instrument_assessment",
                self.actor,
                row.id,
                new={"admission_id": str(row.admission_id), "risk_level": risk_level},
            )
        return row

    def biopsychosocial(self, data):
        _, previous = self.revision(BiopsychosocialAssessment, data)
        if data.status == "REVIEWED" and (
            not previous or previous.status not in {"COMPLETED", "REVIEWED"}
        ):
            raise HTTPException(409, "Complete an assessment before reviewing it")
        if previous and previous.status == "REVIEWED" and data.status == "DRAFT":
            raise HTTPException(409, "A reviewed assessment cannot return to draft")
        return self.save(
            BiopsychosocialAssessment,
            {
                **data.model_dump(),
                "reviewed_by": self.actor.id if data.status == "REVIEWED" else None,
            },
        )

    def risk(self, data):
        self.revision(RiskAssessment, data)
        self.repo.staff(data.assigned_staff_id, "risk.view")
        return self.save(RiskAssessment, data.model_dump())

    def treatment_plan(self, data):
        _, previous = self.revision(TreatmentPlan, data)
        self.repo.staff(data.responsible_professional_id, "treatment_plan.view")
        transitions = {
            "DRAFT": {"DRAFT", "ACTIVE", "CANCELLED"},
            "ACTIVE": {"ACTIVE", "UNDER_REVIEW", "REVISED", "COMPLETED", "CANCELLED"},
            "UNDER_REVIEW": {"UNDER_REVIEW", "REVISED", "ACTIVE", "COMPLETED", "CANCELLED"},
            "REVISED": {"REVISED", "ACTIVE", "UNDER_REVIEW", "COMPLETED", "CANCELLED"},
            "COMPLETED": set(),
            "CANCELLED": set(),
        }
        if previous and data.status not in transitions[previous.status]:
            raise HTTPException(409, "This treatment-plan state transition is not allowed")
        if not previous and data.status not in {"DRAFT", "ACTIVE"}:
            raise HTTPException(409, "New treatment plans must be Draft or Active")
        values = data.model_dump()
        values["objectives"] = [objective.model_dump(mode="json") for objective in data.objectives]
        return self.save(
            TreatmentPlan,
            {
                **values,
                "root_id": previous.root_id if previous else uuid4(),
                "version": previous.version + 1 if previous else 1,
            },
        )

    def case(self, data):
        admission, _ = self.revision(CaseAssignment, data)
        for user_id in {data.case_manager_id, data.counsellor_id, *data.team_member_ids}:
            self.repo.staff(user_id)
        if not data.supersedes_id and self.db.scalar(
            select(CaseAssignment.id).where(
                CaseAssignment.admission_id == admission.id, self.repo.latest(CaseAssignment)
            )
        ):
            raise HTTPException(409, "This admission already has a case assignment; revise it")
        admission.primary_case_manager_id = data.case_manager_id
        admission.assigned_counsellor_id = data.counsellor_id
        admission.updated_by = self.actor.id
        values = data.model_dump()
        values["team_member_ids"] = [str(value) for value in data.team_member_ids]
        return self.save(CaseAssignment, values)

    def therapy(self, data):
        admission, previous = self.revision(TherapySession, data)
        if aware(data.start_at) < aware(admission.admission_date):
            raise HTTPException(422, "Session cannot precede admission")
        if data.status == "COMPLETED" and aware(data.end_at) > utcnow():
            raise HTTPException(422, "Future sessions must remain scheduled")
        if data.confidential or (previous and previous.confidential):
            self.allowed("psychotherapy.create_note")
            if previous and not data.confidential:
                raise HTTPException(
                    422, "Confidential records cannot be reclassified as general therapy"
                )
        self.repo.staff(
            data.therapist_id,
            "psychotherapy.create_note" if data.confidential else "therapy.create_note",
        )
        return self.save(TherapySession, data.model_dump())

    def group(self, data):
        self.repo.staff(data.facilitator_id)
        if data.co_facilitator_id:
            self.repo.staff(data.co_facilitator_id)
        return self.save(GroupSession, data.model_dump())

    def group_attendance(self, group_id, data):
        group = self.repo.require(GroupSession, group_id, lock=True)
        admission, _ = self.revision(GroupAttendance, data)
        if aware(group.start_at) > utcnow() or aware(group.start_at) < aware(
            admission.admission_date
        ):
            raise HTTPException(
                422, "Attendance requires a past or current session during admission"
            )
        if data.private_observation:
            self.allowed("psychotherapy.create_note")
        if data.supersedes_id:
            previous = self.repo.require(GroupAttendance, data.supersedes_id)
            if previous.group_session_id != group.id:
                raise HTTPException(422, "Cannot revise attendance for another group")
            if previous.private_observation:
                self.allowed("psychotherapy.view")
                self.allowed("psychotherapy.create_note")
        elif self.db.scalar(
            select(GroupAttendance.id).where(
                GroupAttendance.group_session_id == group.id,
                GroupAttendance.admission_id == data.admission_id,
                self.repo.latest(GroupAttendance),
            )
        ):
            raise HTTPException(409, "Attendance is already recorded; submit a revision")
        return self.save(GroupAttendance, {**data.model_dump(), "group_session_id": group.id})

    def programme(self, data):
        self.repo.staff(data.facilitator_id)
        return self.save(ProgrammeActivity, data.model_dump())

    def programme_attendance(self, activity_id, data):
        activity = self.repo.require(ProgrammeActivity, activity_id, lock=True)
        admission, previous = self.revision(ProgrammeAttendance, data)
        first = activity.start_at.astimezone(EAT).date()
        days = (data.occurrence_date - first).days
        valid = days >= 0 and (
            activity.repeat_until is None or data.occurrence_date <= activity.repeat_until
        )
        valid = valid and (
            activity.recurrence == "DAILY"
            or (activity.recurrence == "ONCE" and days == 0)
            or (activity.recurrence == "WEEKLY" and days % 7 == 0)
        )
        if not activity.active or not valid:
            raise HTTPException(422, "This date is not a scheduled activity occurrence")
        if (
            data.occurrence_date < admission.admission_date.date()
            or data.occurrence_date > business_today()
        ):
            raise HTTPException(
                422, "Attendance must be during admission and cannot be in the future"
            )
        if activity.programme and activity.programme != admission.programme:
            raise HTTPException(422, "Activity belongs to a different admission programme")
        if previous and (
            previous.activity_id != activity.id or previous.occurrence_date != data.occurrence_date
        ):
            raise HTTPException(422, "A revision cannot change the activity occurrence")
        if not previous and self.db.scalar(
            select(ProgrammeAttendance.id).where(
                ProgrammeAttendance.activity_id == activity.id,
                ProgrammeAttendance.admission_id == data.admission_id,
                ProgrammeAttendance.occurrence_date == data.occurrence_date,
                self.repo.latest(ProgrammeAttendance),
            )
        ):
            raise HTTPException(409, "Attendance is already recorded; submit a revision")
        return self.save(ProgrammeAttendance, {**data.model_dump(), "activity_id": activity.id})

    def schedule(self, start, end, args):
        if start > end or (end - start).days > 92:
            raise HTTPException(422, "Select a schedule period of at most 93 days")
        rows, meta = self.repo.page_records(ProgrammeActivity, **args)
        occurrences = []
        for activity in rows:
            first = activity.start_at.astimezone(EAT).date()
            last = min(
                end, activity.repeat_until or (first if activity.recurrence == "ONCE" else end)
            )
            interval = 7 if activity.recurrence == "WEEKLY" else 1
            current = max(start, first)
            if interval == 7:
                current += timedelta(days=(-(current - first).days) % 7)
            while current <= last and activity.active:
                occurrences.append({**record_out(activity), "occurrence_date": current})
                current += timedelta(days=interval)
        self.access("programme_schedule")
        return {
            "items": sorted(occurrences, key=lambda row: (row["occurrence_date"], row["start_at"])),
            "meta": meta,
        }

    def family(self, data):
        from app.models.clients import ClientContact, Consent

        admission = self.repo.admission(data.admission_id)
        consent = self.repo.require(Consent, data.consent_id, lock=True)
        contact = self.repo.require(ClientContact, data.contact_id, lock=True)
        if (
            consent.client_id != admission.client_id
            or (consent.admission_id and consent.admission_id != admission.id)
            or consent.consent_type != "FAMILY_COMMUNICATION"
            or consent.decision != "GRANTED"
        ):
            raise HTTPException(
                422, "Select a granted family-communication consent for this client and admission"
            )
        now, communicated = utcnow(), aware(data.communicated_at)
        if (
            communicated > now
            or aware(consent.consent_date) > communicated
            or consent.withdrawn_at
            or (consent.expires_at and aware(consent.expires_at) <= now)
        ):
            raise HTTPException(
                422, "Family communication requires a current valid consent at the time of contact"
            )
        if (
            contact.client_id != admission.client_id
            or not contact.active
            or not contact.authorized_contact
        ):
            raise HTTPException(422, "Select an active authorized contact for this client")
        return self.save(FamilyCommunication, data.model_dump(exclude={"scope_confirmed"}))

    def case_dashboard(self, args):
        from sqlalchemy import func, or_

        from app.models.clients import Admission, Client

        statement = select(Admission).where(
            Admission.facility_id == self.actor.facility_id,
            Admission.primary_case_manager_id == self.actor.id,
            Admission.status.in_(
                ["ACTIVE", "ON_LEAVE", "HOSPITALIZED", "AWOL", "DISCHARGE_PENDING"]
            ),
        )
        if args.get("admission_id"):
            statement = statement.where(Admission.id == args["admission_id"])
        if args.get("q"):
            needle = f"%{args['q']}%"
            statement = statement.join(Client, Admission.client_id == Client.id).where(
                or_(
                    Client.first_name.ilike(needle),
                    Client.surname.ilike(needle),
                    Admission.admission_number.ilike(needle),
                )
            )
        total = self.db.scalar(select(func.count()).select_from(statement.subquery()))
        admissions = list(
            self.db.scalars(
                statement.order_by(Admission.admission_date.desc())
                .offset((args["page"] - 1) * args["page_size"])
                .limit(args["page_size"])
            )
        )
        today = business_today()
        items = []
        for admission in admissions:
            client = self.repo.client(admission.client_id)
            assignment = self.db.scalar(
                select(CaseAssignment).where(
                    CaseAssignment.admission_id == admission.id,
                    CaseAssignment.facility_id == self.actor.facility_id,
                    self.repo.latest(CaseAssignment),
                )
            )
            risks = (
                list(
                    self.db.scalars(
                        select(RiskAssessment).where(
                            RiskAssessment.admission_id == admission.id,
                            RiskAssessment.facility_id == self.actor.facility_id,
                            RiskAssessment.status == "ACTIVE",
                            self.repo.latest(RiskAssessment),
                        )
                    )
                )
                if "risk.view" in permission_codes(self.actor)
                else []
            )
            plans = (
                list(
                    self.db.scalars(
                        select(TreatmentPlan).where(
                            TreatmentPlan.admission_id == admission.id,
                            TreatmentPlan.facility_id == self.actor.facility_id,
                            TreatmentPlan.status.in_(["ACTIVE", "UNDER_REVIEW", "REVISED"]),
                            self.repo.latest(TreatmentPlan),
                        )
                    )
                )
                if "treatment_plan.view" in permission_codes(self.actor)
                else []
            )
            sessions = (
                list(
                    self.db.scalars(
                        select(TherapySession).where(
                            TherapySession.admission_id == admission.id,
                            TherapySession.facility_id == self.actor.facility_id,
                            self.repo.latest(TherapySession),
                            TherapySession.confidential.is_(False)
                            if "psychotherapy.view" not in permission_codes(self.actor)
                            else True,
                        )
                    )
                )
                if "therapy.view" in permission_codes(self.actor)
                else []
            )
            assessment_due = assignment.assessment_due if assignment else None
            items.append(
                {
                    "id": assignment.id if assignment else admission.id,
                    "admission_id": admission.id,
                    "admission_number": admission.admission_number,
                    "client_number": client.client_number,
                    "client_name": f"{client.first_name} {client.surname}",
                    "status": admission.status,
                    "case_profile_required": assignment is None,
                    "assessment_due": assessment_due,
                    "assessment_overdue": bool(assessment_due and assessment_due < today),
                    "family_meeting_due": assignment.family_meeting_due if assignment else None,
                    "discharge_preparation_due": assignment.discharge_preparation_due
                    if assignment
                    else None,
                    "treatment_reviews": [
                        {"id": p.id, "review_date": p.review_date, "overdue": p.review_date < today}
                        for p in plans
                    ],
                    "active_risks": [
                        {
                            "id": r.id,
                            "level": r.level,
                            "risk_type": r.risk_type,
                            "review_date": r.review_date,
                        }
                        for r in risks
                    ],
                    "missed_sessions": sum(s.status == "MISSED" for s in sessions),
                    "upcoming_sessions": [
                        {"id": s.id, "start_at": s.start_at}
                        for s in sessions
                        if s.status == "SCHEDULED" and aware(s.start_at) >= utcnow()
                    ],
                }
            )
        self.access("case_dashboard")
        return {
            "items": items,
            "meta": {"page": args["page"], "page_size": args["page_size"], "total": total},
            "aftercare_available": False,
        }

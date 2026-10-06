from fastapi import HTTPException
from sqlalchemy import select

from app.audit.service import audit
from app.core.permissions import aware
from app.core.time import EAT
from app.models.clients import (
    Admission,
    AdmissionStatusHistory,
    Bed,
    BedAssignment,
    Client,
    ClientContact,
    ClientRevision,
    Consent,
    EpisodeOfCare,
    PropertyItem,
    Referral,
    Room,
    Screening,
    Wing,
)
from app.models.identity import utcnow
from app.repositories.clients import ClientRepository

ADMISSION_TRANSITIONS = {
    "PENDING": {"ACTIVE"},
    "ACTIVE": {"ON_LEAVE", "HOSPITALIZED", "AWOL", "DISCHARGE_PENDING"},
    "ON_LEAVE": {"ACTIVE", "HOSPITALIZED", "AWOL", "DISCHARGE_PENDING"},
    "HOSPITALIZED": {"ACTIVE", "DISCHARGE_PENDING"},
    "AWOL": {"ACTIVE", "DISCHARGE_PENDING"},
    "DISCHARGE_PENDING": {"ACTIVE"},
}
REFERRAL_TRANSITIONS = {
    "NEW": {"SCREENING", "DEFERRED", "DECLINED", "REFERRED_ELSEWHERE"},
    "SCREENING": {"DEFERRED", "DECLINED", "REFERRED_ELSEWHERE"},
    "DEFERRED": {"SCREENING", "DECLINED", "REFERRED_ELSEWHERE"},
    "ACCEPTED": {"DEFERRED", "DECLINED"},
}


class ClientService:
    def __init__(self, db, request, actor):
        self.db, self.request, self.actor = db, request, actor
        self.repo = ClientRepository(db, actor)

    def log(self, action, record, previous=None, new=None, reason=None):
        audit(
            self.db,
            self.request,
            action,
            record.__tablename__,
            self.actor,
            record.id,
            previous=previous,
            new=new,
            reason=reason,
        )

    def add(self, model, values):
        row = model(**values, facility_id=self.actor.facility_id, created_by=self.actor.id)
        self.db.add(row)
        self.db.flush()
        return row

    def save_client(self, data, record_id=None):
        values = data.model_dump(exclude={"reason"}, mode="json")
        values["date_of_birth"] = data.date_of_birth
        if record_id and "photo_reference" not in data.model_fields_set:
            values.pop("photo_reference", None)
        if values.get("photo_reference"):
            from uuid import UUID

            from app.models.clients import IntakeDocument

            try:
                document_id = UUID(values["photo_reference"])
            except ValueError:
                raise HTTPException(422, "Use the client photo upload workflow") from None
            document = self.repo.require(IntakeDocument, document_id)
            if not record_id or document.client_id != record_id or document.category != "PHOTO":
                raise HTTPException(422, "Photo must belong to this client")
        for key in ("national_id", "passport_number"):
            if self.repo.identifier_duplicate(key, values[key], record_id):
                raise HTTPException(
                    409, f"A client with this {key.replace('_', ' ')} already exists"
                )
        if record_id:
            row = self.repo.client(record_id, lock=True)
            if data.deceased and self.repo.open_admission(row.id):
                raise HTTPException(
                    409,
                    (
                        "Close the current admission through the discharge workflow "
                        "before marking the client deceased"
                    ),
                )
            previous = {"active": row.active, "deceased": row.deceased}
            for key, value in values.items():
                setattr(row, key, value)
            row.updated_by = self.actor.id
        else:
            values["client_number"] = self.repo.number(
                "CLIENT",
                __import__("app.core.time", fromlist=["business_today"]).business_today().year,
            )
            row = self.add(Client, values)
            previous = None
        from fastapi.encoders import jsonable_encoder

        from app.schemas.clients import record_out

        self.add(
            ClientRevision,
            {
                "client_id": row.id,
                "snapshot": jsonable_encoder(record_out(row)),
                "reason": getattr(data, "reason", "Initial registration"),
            },
        )
        self.log(
            "client.updated" if record_id else "client.created",
            row,
            previous,
            {
                "client_number": row.client_number,
                "active": row.active,
                "deceased": row.deceased,
                "changed_fields": list(values),
            },
            getattr(data, "reason", None),
        )
        return row

    def contact(self, client_id, data, record_id=None):
        self.repo.client(client_id)
        if record_id:
            row = self.repo.require(ClientContact, record_id, lock=True)
            if row.client_id != client_id:
                raise HTTPException(404, "Record not found")
            for key, value in data.model_dump(mode="json").items():
                setattr(row, key, value)
            row.updated_by = self.actor.id
        else:
            row = self.add(ClientContact, dict(data.model_dump(mode="json"), client_id=client_id))
        self.log("client.contact_saved", row, new={"kind": row.kind, "active": row.active})
        return row

    def referral(self, data):
        client = self.repo.client(data.client_id)
        if not client.active or client.deceased:
            raise HTTPException(409, "Referral requires an active client")
        values = data.model_dump(mode="json")
        values.update(client_id=data.client_id, referral_date=data.referral_date)
        if values["documents"]:
            # The document subsystem is a later phase. Reject unverifiable references.
            raise HTTPException(
                422,
                (
                    "Upload referral documents after creating the referral; "
                    "leave document references empty during initial creation"
                ),
            )
        row = self.add(Referral, values)
        self.log(
            "referral.created",
            row,
            new={"client_id": str(row.client_id), "status": row.status, "source": row.source},
        )
        return row

    def referral_status(self, record_id, data):
        row = self.repo.require(Referral, record_id, lock=True)
        if data.status not in REFERRAL_TRANSITIONS.get(row.status, set()):
            raise HTTPException(
                409, "Invalid referral transition; acceptance requires a suitable screening"
            )
        previous = row.status
        row.status, row.decision_reason, row.updated_by = data.status, data.reason, self.actor.id
        self.log(
            "referral.status_changed",
            row,
            {"status": previous},
            {"status": row.status},
            data.reason,
        )
        return row

    def screen(self, referral_id, data):
        referral = self.repo.require(Referral, referral_id, lock=True)
        if referral.status not in {"NEW", "SCREENING", "DEFERRED"}:
            raise HTTPException(409, "Only new, screening or deferred referrals can be screened")
        row = self.add(Screening, dict(data.model_dump(), referral_id=referral.id))
        previous = referral.status
        referral.status = {
            "SUITABLE": "ACCEPTED",
            "DECLINED": "DECLINED",
            "EXTERNAL_REFERRAL": "REFERRED_ELSEWHERE",
        }.get(data.decision, "DEFERRED")
        referral.decision_reason, referral.updated_by = data.reason, self.actor.id
        self.log(
            "screening.completed",
            row,
            new={"referral_id": str(referral.id), "decision": row.decision},
        )
        self.log(
            "referral.status_changed", referral, {"status": previous}, {"status": referral.status}
        )
        return row

    def admit(self, data):
        client = self.repo.client(data.client_id, lock=True)
        if not client.active or client.deceased:
            raise HTTPException(409, "Admission requires an active living client")
        if self.repo.open_admission(client.id):
            raise HTTPException(409, "This client already has an open admission")
        referral = self.repo.require(Referral, data.referral_id, lock=True)
        if referral.client_id != client.id or referral.status != "ACCEPTED":
            raise HTTPException(409, "Choose this client's accepted and screened referral")
        if data.admission_date.astimezone(EAT).date() < referral.referral_date:
            raise HTTPException(422, "Admission cannot precede the referral")
        for field in (
            "assigned_counsellor_id",
            "assigned_clinician_id",
            "assigned_nurse_id",
            "primary_case_manager_id",
        ):
            self.validate_staff_assignment(field, getattr(data, field))
        row = self.add(
            Admission,
            dict(
                data.model_dump(),
                admission_number=self.repo.number(
                    "ADMISSION", data.admission_date.astimezone(EAT).year
                ),
            ),
        )
        self.add(
            EpisodeOfCare,
            {"admission_id": row.id, "client_id": row.client_id, "started_at": row.admission_date},
        )
        referral.status, referral.updated_by = "CONVERTED_TO_ADMISSION", self.actor.id
        self.log(
            "admission.created",
            row,
            new={
                "client_id": str(row.client_id),
                "status": row.status,
                "admission_number": row.admission_number,
            },
        )
        self.log(
            "referral.converted", referral, {"status": "ACCEPTED"}, {"status": referral.status}
        )
        return row

    def admission_status(self, record_id, data):
        row = self.repo.admission(record_id, writable=False, lock=True)
        if data.status not in ADMISSION_TRANSITIONS.get(row.status, set()):
            raise HTTPException(
                409,
                "Invalid admission transition; final discharge is managed in the discharge module",
            )
        if data.status == "ACTIVE" and row.status == "PENDING":
            treatment = self.db.scalar(
                select(Consent).where(
                    Consent.admission_id == row.id,
                    Consent.decision == "GRANTED",
                    Consent.consent_type == "TREATMENT",
                    Consent.withdrawn_at.is_(None),
                    Consent.consent_date <= utcnow(),
                    ((Consent.expires_at.is_(None)) | (Consent.expires_at > utcnow())),
                )
            )
            if (
                not row.client_rights_acknowledged
                or not row.treatment_agreement
                or treatment is None
            ):
                raise HTTPException(
                    409,
                    (
                        "Activation requires rights acknowledgment, treatment agreement "
                        "and valid treatment consent"
                    ),
                )
            if self.repo.current_assignment(row.id) is None:
                raise HTTPException(409, "Assign a bed before activating a residential admission")
        previous = row.status
        row.status, row.updated_by = data.status, self.actor.id
        self.add(
            AdmissionStatusHistory,
            {
                "admission_id": row.id,
                "previous_status": previous,
                "new_status": row.status,
                "reason": data.reason,
            },
        )
        self.log(
            "admission.status_changed",
            row,
            {"status": previous},
            {"status": row.status},
            data.reason,
        )
        return row

    def update_intake(self, record_id, data):
        from fastapi.encoders import jsonable_encoder
        from sqlalchemy import func

        from app.models.clients import AdmissionIntakeRevision
        from app.schemas.clients import record_out

        row = self.repo.admission(record_id, writable=False, lock=True)
        if row.status in {"DISCHARGED", "TRANSFERRED", "DECEASED"}:
            raise HTTPException(409, "Closed admission intake cannot be amended")
        if row.status != "PENDING" and (
            not data.client_rights_acknowledged or not data.treatment_agreement
        ):
            raise HTTPException(
                409, "Current admissions must retain their required acknowledgments"
            )
        version = (
            self.db.scalar(
                select(func.max(AdmissionIntakeRevision.version)).where(
                    AdmissionIntakeRevision.admission_id == row.id
                )
            )
            or 0
        )
        if not version:
            self.add(
                AdmissionIntakeRevision,
                {
                    "admission_id": row.id,
                    "version": 1,
                    "snapshot": jsonable_encoder(record_out(row)),
                    "reason": "Original intake before amendment",
                },
            )
            version = 1
        for key, value in data.model_dump(exclude={"reason"}).items():
            setattr(row, key, value)
        row.updated_by = self.actor.id
        self.db.flush()
        self.add(
            AdmissionIntakeRevision,
            {
                "admission_id": row.id,
                "version": version + 1,
                "snapshot": jsonable_encoder(record_out(row)),
                "reason": data.reason,
            },
        )
        self.log(
            "admission.intake_amended",
            row,
            new={"version": version + 1},
            reason="Reason stored with intake revision",
        )
        return row

    def validate_staff_assignment(self, field, user_id):
        if user_id is None:
            return
        from app.core.security import permission_codes

        person = self.repo.staff(user_id)
        required = {
            "assigned_clinician_id": "clinical.create_note",
            "assigned_nurse_id": "nursing.record",
            "assigned_counsellor_id": "therapy.create_note",
        }.get(field)
        if required and required not in permission_codes(person):
            raise HTTPException(422, "Assigned professional lacks the required care permission")

    def assignments(self, record_id, data):
        row = self.repo.admission(record_id, writable=False, lock=True)
        if row.status in {"DISCHARGED", "TRANSFERRED", "DECEASED"}:
            raise HTTPException(409, "Closed admissions cannot be reassigned")
        fields = data.model_dump(exclude={"reason"})
        previous = {key: str(getattr(row, key)) if getattr(row, key) else None for key in fields}
        for key, value in fields.items():
            self.validate_staff_assignment(key, value)
            setattr(row, key, value)
        row.updated_by = self.actor.id
        self.log(
            "admission.team_changed",
            row,
            previous,
            {key: str(value) if value else None for key, value in fields.items()},
            data.reason,
        )
        return row

    def consent(self, admission_id, data):
        admission = self.repo.admission(admission_id, writable=False, lock=True)
        if admission.status in {"DISCHARGED", "TRANSFERRED", "DECEASED"}:
            raise HTTPException(409, "Closed admission cannot receive new consent")
        if data.consent_date < aware(admission.admission_date):
            raise HTTPException(422, "Consent date cannot precede this admission")
        existing = self.db.scalar(
            select(Consent).where(
                Consent.admission_id == admission.id,
                Consent.consent_type == data.consent_type,
                Consent.withdrawn_at.is_(None),
                Consent.decision == "GRANTED",
                ((Consent.expires_at.is_(None)) | (Consent.expires_at > utcnow())),
            )
        )
        if existing:
            raise HTTPException(
                409, "Withdraw the existing active consent before recording a replacement decision"
            )
        row = self.add(
            Consent,
            dict(data.model_dump(), client_id=admission.client_id, admission_id=admission.id),
        )
        self.log(
            "consent.recorded",
            row,
            new={"type": row.consent_type, "decision": row.decision, "version": row.version},
        )
        return row

    def withdraw_consent(self, record_id, data):
        row = self.repo.require(Consent, record_id, lock=True)
        if row.withdrawn_at or row.decision != "GRANTED":
            raise HTTPException(409, "Only a granted, unwithdrawn consent can be withdrawn")
        row.withdrawn_at, row.withdrawal_reason, row.updated_by = (
            utcnow(),
            data.reason,
            self.actor.id,
        )
        self.log("consent.withdrawn", row, new={"withdrawn": True}, reason=data.reason)
        return row

    def property_item(self, admission_id, data):
        admission = self.repo.admission(admission_id, writable=False)
        if admission.status in {"DISCHARGED", "TRANSFERRED", "DECEASED"}:
            raise HTTPException(409, "Closed admission cannot receive property")
        row = self.add(
            PropertyItem,
            dict(data.model_dump(), admission_id=admission.id, received_by=self.actor.id),
        )
        self.log("property.received", row, new={"category": row.category, "quantity": row.quantity})
        return row

    def return_property(self, record_id, data):
        row = self.repo.require(PropertyItem, record_id, lock=True)
        if row.returned_at:
            raise HTTPException(409, "Property has already been returned")
        row.returned_at, row.returned_by, row.return_reason, row.updated_by = (
            utcnow(),
            self.actor.id,
            data.reason,
            self.actor.id,
        )
        self.log("property.returned", row, new={"returned": True}, reason=data.reason)
        return row

    def residential(self, model, data):
        values = data.model_dump()
        if model is Room:
            wing = self.repo.require(Wing, data.wing_id)
            if not wing.active:
                raise HTTPException(422, "Select an active wing")
        if model is Bed:
            room = self.repo.require(Room, data.room_id)
            if not room.active:
                raise HTTPException(422, "Select an active room")
        filters = [model.name == data.name, model.facility_id == self.actor.facility_id]
        if model is Bed:
            filters.append(Bed.room_id == data.room_id)
        if self.db.scalar(select(model).where(*filters)):
            raise HTTPException(409, "A record with this name already exists")
        row = self.add(model, values)
        self.log("residential.created", row, new={"name": row.name})
        return row

    def bed_status(self, record_id, data):
        row = self.repo.require(Bed, record_id, lock=True)
        if data.status not in {"AVAILABLE", "RESERVED", "CLEANING", "MAINTENANCE", "UNAVAILABLE"}:
            raise HTTPException(422, "Occupancy changes through bed assignment only")
        if row.status == "OCCUPIED" or self.db.scalar(
            select(BedAssignment).where(
                BedAssignment.bed_id == row.id, BedAssignment.ended_at.is_(None)
            )
        ):
            raise HTTPException(409, "Release the bed assignment before changing bed status")
        previous = row.status
        row.status, row.updated_by = data.status, self.actor.id
        self.log(
            "bed.status_changed", row, {"status": previous}, {"status": row.status}, data.reason
        )
        return row

    def assign_bed(self, admission_id, data):
        admission = self.repo.admission(admission_id, writable=False, lock=True)
        if admission.status in {"DISCHARGED", "TRANSFERRED", "DECEASED"}:
            raise HTTPException(409, "Closed admissions cannot receive a bed")
        current = self.repo.current_assignment(admission.id, lock=True)
        # Consistent sorted bed locks prevent concurrent opposite transfers from deadlocking.
        bed_ids = sorted({data.bed_id} | ({current.bed_id} if current else set()), key=str)
        beds = {record_id: self.repo.require(Bed, record_id, lock=True) for record_id in bed_ids}
        bed = beds[data.bed_id]
        if current and current.bed_id == bed.id:
            raise HTTPException(409, "Admission already occupies this bed")
        if bed.status not in {"AVAILABLE", "RESERVED"} or self.db.scalar(
            select(BedAssignment).where(
                BedAssignment.bed_id == bed.id, BedAssignment.ended_at.is_(None)
            )
        ):
            raise HTTPException(409, "Bed is not available")
        room = self.repo.require(Room, bed.room_id)
        wing = self.repo.require(Wing, room.wing_id)
        client = self.repo.client(admission.client_id)
        if (
            not room.active
            or not wing.active
            or (room.sex_restriction and room.sex_restriction != client.sex)
        ):
            raise HTTPException(409, "Room is inactive or unsuitable for this client")
        if current:
            current.ended_at, current.updated_by = utcnow(), self.actor.id
            beds[current.bed_id].status = "CLEANING"
            beds[current.bed_id].updated_by = self.actor.id
            self.db.flush()  # End old assignment before inserting the unique current assignment.
        bed.status, bed.updated_by = "OCCUPIED", self.actor.id
        row = self.add(
            BedAssignment, {"bed_id": bed.id, "admission_id": admission.id, "reason": data.reason}
        )
        self.log(
            "bed.transferred" if current else "bed.assigned",
            row,
            {"bed_id": str(current.bed_id)} if current else None,
            {"bed_id": str(bed.id), "admission_id": str(admission.id)},
            data.reason,
        )
        return row

    def release_bed(self, admission_id, data):
        admission = self.repo.admission(admission_id, writable=False, lock=True)
        if admission.status in {"ACTIVE", "ON_LEAVE", "HOSPITALIZED", "AWOL", "DISCHARGE_PENDING"}:
            raise HTTPException(
                409,
                "Current admissions retain their bed; transfer or use the final discharge workflow",
            )
        current = self.repo.current_assignment(admission.id, lock=True)
        if current is None:
            raise HTTPException(409, "Admission has no current bed")
        bed = self.repo.require(Bed, current.bed_id, lock=True)
        current.ended_at, current.updated_by = utcnow(), self.actor.id
        bed.status, bed.updated_by = "CLEANING", self.actor.id
        self.log("bed.released", current, new={"ended": True}, reason=data.reason)
        return current

from uuid import UUID

from sqlalchemy import or_, select

from app.models.clinical import ClinicalRevision, LaboratoryAttachment, LaboratoryResult
from app.repositories.care import CareRepository


class ClinicalRepository(CareRepository):
    def page(self, model, *args, q="", fields=(), filters=(), **kwargs):
        if q:
            from app.models.clients import Admission, Client

            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            matches = select(Client.id).where(
                Client.facility_id == self.actor.facility_id,
                or_(
                    *(
                        f.ilike(f"%{escaped}%", escape="\\")
                        for f in (Client.first_name, Client.surname, Client.client_number)
                    )
                ),
            )
            predicates = []
            if hasattr(model, "client_id"):
                predicates.append(model.client_id.in_(matches))
            if hasattr(model, "admission_id"):
                admissions = select(Admission.id).where(
                    Admission.facility_id == self.actor.facility_id,
                    or_(
                        Admission.client_id.in_(matches),
                        Admission.admission_number.ilike(f"%{escaped}%", escape="\\"),
                    ),
                )
                predicates.append(model.admission_id.in_(admissions))
            for key in (
                "encounter_type",
                "order_type",
                "shift",
                "test",
                "substance",
                "diagnosis",
                "sample_type",
            ):
                if hasattr(model, key):
                    predicates.append(getattr(model, key).ilike(f"%{escaped}%", escape="\\"))
            if predicates:
                filters = (*filters, or_(*predicates))
        return super().page(model, *args, q="", fields=fields, filters=filters, **kwargs)

    def revisions(self, entity_type: str, entity_id: UUID):
        return list(
            self.db.scalars(
                select(ClinicalRevision)
                .where(
                    ClinicalRevision.facility_id == self.actor.facility_id,
                    ClinicalRevision.entity_type == entity_type,
                    ClinicalRevision.entity_id == entity_id,
                )
                .order_by(ClinicalRevision.version)
            )
        )

    def results(self, request_id: UUID):
        return list(
            self.db.scalars(
                select(LaboratoryResult)
                .where(
                    LaboratoryResult.facility_id == self.actor.facility_id,
                    LaboratoryResult.request_id == request_id,
                )
                .order_by(LaboratoryResult.created_at, LaboratoryResult.id)
            )
        )

    def attachments(self, request_id: UUID):
        # Explicit metadata projection avoids pulling PDF bytes into list responses.
        return [
            dict(row._mapping)
            for row in self.db.execute(
                select(
                    LaboratoryAttachment.id,
                    LaboratoryAttachment.filename,
                    LaboratoryAttachment.size,
                    LaboratoryAttachment.sha256,
                    LaboratoryAttachment.created_at,
                    LaboratoryAttachment.created_by,
                ).where(
                    LaboratoryAttachment.facility_id == self.actor.facility_id,
                    LaboratoryAttachment.request_id == request_id,
                )
            )
        ]

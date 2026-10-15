"""Global unified quick search API across ReHUB records with RBAC filtering."""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import current_user
from app.core.security import permission_codes
from app.models.billing import Invoice
from app.models.clients import Admission, Client, Referral
from app.models.clinical import ClinicalEncounter
from app.models.identity import User
from app.models.inventory import StoreItem
from app.models.medication import Medication
from app.models.residential import Incident
from app.models.staff import StaffProfile

router = APIRouter(prefix="/search", tags=["Global Search"])


@router.get("/quick")
def quick_search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    """Unified multi-entity quick search respecting user RBAC permissions."""
    clean_q = q.strip().replace("%", "\\%").replace("_", "\\_")
    needle = f"%{clean_q}%"
    perms = permission_codes(actor)
    facility_id = actor.facility_id

    results = {}
    total_matches = 0

    # 1. Clients
    if "client.view" in perms:
        stmt = (
            select(Client)
            .where(
                Client.facility_id == facility_id,
                or_(
                    Client.client_number.ilike(needle),
                    Client.first_name.ilike(needle),
                    Client.middle_name.ilike(needle),
                    Client.surname.ilike(needle),
                    Client.phone.ilike(needle),
                    Client.national_id.ilike(needle),
                ),
            )
            .order_by(Client.created_at.desc())
            .limit(limit)
        )
        clients = db.scalars(stmt).all()
        client_items = [
            {
                "id": str(c.id),
                "code": c.client_number,
                "title": f"{c.first_name} {c.surname}".strip(),
                "subtitle": f"{c.client_number} · {c.phone or 'No phone'} · {c.sex}",
                "type": "clients",
                "url": f"/clients?q={c.client_number}",
            }
            for c in clients
        ]
        if client_items:
            results["clients"] = client_items
            total_matches += len(client_items)

    # 2. Admissions
    if "admission.view" in perms or "client.view" in perms or "clinical.view" in perms:
        stmt = (
            select(Admission, Client)
            .join(Client, Admission.client_id == Client.id)
            .where(
                Admission.facility_id == facility_id,
                or_(
                    Admission.admission_number.ilike(needle),
                    Client.first_name.ilike(needle),
                    Client.surname.ilike(needle),
                    Client.client_number.ilike(needle),
                ),
            )
            .order_by(Admission.admission_date.desc())
            .limit(limit)
        )
        admissions = db.execute(stmt).all()
        admission_items = [
            {
                "id": str(adm.id),
                "code": adm.admission_number,
                "title": f"{cli.first_name} {cli.surname}".strip(),
                "subtitle": f"{adm.admission_number} · {adm.status} · {adm.programme}",
                "type": "admissions",
                "url": f"/admissions?q={adm.admission_number}",
            }
            for adm, cli in admissions
        ]
        if admission_items:
            results["admissions"] = admission_items
            total_matches += len(admission_items)

    # 3. Medications
    if "medication.view" in perms:
        stmt = (
            select(Medication)
            .where(
                Medication.facility_id == facility_id,
                or_(
                    Medication.reference_code.ilike(needle),
                    Medication.generic_name.ilike(needle),
                    Medication.brand_name.ilike(needle),
                ),
            )
            .order_by(Medication.generic_name.asc())
            .limit(limit)
        )
        meds = db.scalars(stmt).all()
        med_items = [
            {
                "id": str(m.id),
                "code": m.reference_code,
                "title": f"{m.generic_name} {m.strength}".strip(),
                "subtitle": f"{m.reference_code} · {m.formulation} · {'Active' if m.active else 'Inactive'}",
                "type": "medications",
                "url": f"/medication?q={m.reference_code}",
            }
            for m in meds
        ]
        if med_items:
            results["medications"] = med_items
            total_matches += len(med_items)

    # 4. Invoices
    if "billing.view" in perms:
        stmt = (
            select(Invoice, Client)
            .outerjoin(Client, Invoice.client_id == Client.id)
            .where(
                Invoice.facility_id == facility_id,
                or_(
                    Invoice.invoice_number.ilike(needle),
                    Client.first_name.ilike(needle),
                    Client.surname.ilike(needle),
                ),
            )
            .order_by(Invoice.created_at.desc())
            .limit(limit)
        )
        invoices = db.execute(stmt).all()
        invoice_items = [
            {
                "id": str(inv.id),
                "code": inv.invoice_number,
                "title": f"{inv.invoice_number} · KSh {inv.total_amount:,.2f}",
                "subtitle": f"Client: {cli.first_name + ' ' + cli.surname if cli else 'N/A'} · Status: {inv.status}",
                "type": "invoices",
                "url": f"/billing?q={inv.invoice_number}",
            }
            for inv, cli in invoices
        ]
        if invoice_items:
            results["invoices"] = invoice_items
            total_matches += len(invoice_items)

    # 5. Staff
    if "staff.view" in perms:
        stmt = (
            select(
                StaffProfile.id,
                StaffProfile.employee_number,
                StaffProfile.designation,
                StaffProfile.department,
                User.full_name,
            )
            .join(User, StaffProfile.user_id == User.id)
            .where(
                StaffProfile.facility_id == facility_id,
                or_(
                    StaffProfile.employee_number.ilike(needle),
                    User.full_name.ilike(needle),
                    StaffProfile.designation.ilike(needle),
                    StaffProfile.department.ilike(needle),
                ),
            )
            .order_by(StaffProfile.employee_number.asc())
            .limit(limit)
        )
        staff_list = db.execute(stmt).all()
        staff_items = [
            {
                "id": str(sp_id),
                "code": emp_num,
                "title": full_name.strip(),
                "subtitle": f"{emp_num} · {desig} ({dept})",
                "type": "staff",
                "url": f"/staff?q={emp_num}",
            }
            for sp_id, emp_num, desig, dept, full_name in staff_list
        ]
        if staff_items:
            results["staff"] = staff_items
            total_matches += len(staff_items)

    # 6. Incidents
    if "residential.view" in perms:
        stmt = (
            select(Incident)
            .where(
                Incident.facility_id == facility_id,
                or_(
                    Incident.reference_code.ilike(needle),
                    Incident.category.ilike(needle),
                    Incident.location.ilike(needle),
                ),
            )
            .order_by(Incident.created_at.desc())
            .limit(limit)
        )
        incidents = db.scalars(stmt).all()
        incident_items = [
            {
                "id": str(inc.id),
                "code": inc.reference_code,
                "title": f"{inc.reference_code} · {inc.category}",
                "subtitle": f"Severity: {inc.severity} · Status: {inc.status}",
                "type": "incidents",
                "url": f"/residential?q={inc.reference_code}",
            }
            for inc in incidents
        ]
        if incident_items:
            results["incidents"] = incident_items
            total_matches += len(incident_items)

    # 7. Stock Items
    if "inventory.view" in perms:
        stmt = (
            select(StoreItem)
            .where(
                StoreItem.facility_id == facility_id,
                or_(
                    StoreItem.code.ilike(needle),
                    StoreItem.name.ilike(needle),
                    StoreItem.category.ilike(needle),
                ),
            )
            .order_by(StoreItem.name.asc())
            .limit(limit)
        )
        items = db.scalars(stmt).all()
        store_items = [
            {
                "id": str(it.id),
                "code": it.code,
                "title": f"{it.name} ({it.unit_of_measure})",
                "subtitle": f"{it.code} · Stock: {it.current_stock} · Cat: {it.category}",
                "type": "inventory",
                "url": f"/inventory?q={it.code}",
            }
            for it in items
        ]
        if store_items:
            results["inventory"] = store_items
            total_matches += len(store_items)

    return {"results": results, "total_matches": total_matches}

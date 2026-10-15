"""Database seed script for ReHUB / ARS RMS.

Populates initial facility, departments, permissions, roles, and reference catalogues.
When development=True, provisions default development staff accounts.
"""

import argparse
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import password_hasher
from app.models.identity import Department, Facility, Permission, Role, User
from app.seed_care import PERMISSIONS as CARE_PERMISSIONS

logger = logging.getLogger("rehub.seed")

ALL_PERMISSIONS = {
    # Administration & Foundation
    "users.manage": "Manage staff accounts and credentials",
    "roles.manage": "Manage institutional roles and permission bindings",
    "departments.manage": "Manage facility departments",
    "settings.manage": "Manage institution settings and facility profile",
    "audit.view": "Inspect immutable audit trails",
    "system.view": "View system health and operational status",
    # Client Registry & Intake
    "client.view": "View client registry records",
    "client.create": "Register new clients",
    "client.update": "Update client demographic and contact details",
    "referral.view": "View referral records",
    "referral.create": "Create new client referrals",
    "referral.update": "Update referral status and triage details",
    "screening.view": "View pre-admission risk screenings",
    "screening.create": "Conduct pre-admission risk screenings",
    "admission.view": "View admission records",
    "admission.create": "Admit clients into residential programme",
    "admission.update": "Update admission details and statuses",
    "admission.assign": "Assign primary staff and case managers",
    "admission.property": "Manage client property, valuables and custody",
    "consent.view": "View signed and versioned consent records",
    "consent.create": "Record client and family consent documents",
    "consent.withdraw": "Process consent revocation and restrictions",
    # Residential Operations & Safeguarding
    "residential.view": "View wings, rooms, beds and residential movements",
    "residential.edit": "Manage beds, rooms, leave and visitor logs",
    "residential.manage": "Configure wings, bed occupancy and maintenance",
    "residential.assign": "Allocate and transfer client bed assignments",
    "safeguarding.view": "View confidential safeguarding records",
    "safeguarding.edit": "File safeguarding concerns, incidents and addenda",
    # Assessments & Rehabilitation
    "assessment.view": "View biopsychosocial and psychometric assessments",
    "assessment.record": "Record biopsychosocial and psychometric assessments",
    "assessment.configure": "Configure assessment instruments and substances",
    "risk.view": "View clinical and suicide risk assessments",
    "risk.record": "Record clinical and suicide risk assessments",
    "treatment_plan.view": "View client treatment plans and MDT coordination",
    "case_management.view": "View client treatment plans and MDT coordination",
    "treatment_plan.manage": "Manage treatment plans and case assignments",
    "treatment_plan.record": "Record treatment plan interventions",
    "treatment_plan.review": "Review treatment plans and milestone reviews",
    "family.view": "View family communication records",
    "family.record": "Record family communication events and progress sharing",
    "programme.view": "View rehabilitation schedule and activities",
    "programme.manage": "Manage daily/weekly activity schedules",
    "therapy.view": "View therapy sessions and progress notes",
    "therapy.create_note": "Record confidential psychotherapy and counselling notes",
    "psychotherapy.view": "View confidential psychotherapy notes and private observations",
    "psychotherapy.create_note": "Record confidential psychotherapy session notes",
    # Clinical & Nursing Care
    "clinical.view": "View medical encounters, diagnoses and orders",
    "clinical.edit": "Manage clinician encounters and diagnoses",
    "clinical.create_note": "Record doctor consultations and progress notes",
    "clinical.record_vitals": "Record vital sign observations",
    "clinical.manage_orders": "Issue clinician orders and lab requests",
    "nursing.view": "View nursing dashboard, observations and handovers",
    "nursing.record": "Record vital signs, nursing notes and shift handovers",
    "lab.view": "View lab investigation requests and toxicology panels",
    "lab.order": "Order laboratory investigations",
    "lab.result": "Record and review laboratory and drug screen results",
    # Medication & Pharmacy
    "medication.view": "View active medication orders and catalogues",
    "medication.prescribe": "Prescribe medications and dosage instructions",
    "medication.administer": "Administer medication and record eMAR outcomes",
    "pharmacy.view": "View pharmacy stock levels and batch registry",
    "pharmacy.manage": "Manage drug catalogue, supplier receipts and adjustments",
    "pharmacy.dispense": "Dispense pharmaceuticals to wards and clients",
    # Discharge & Recovery
    "discharge.view": "View discharge plans, summaries and aftercare cases",
    "discharge.edit": "Manage discharge readiness, summary and recovery tracking",
    # Billing & Finance
    "billing.view": "View invoices, fee catalogues and client statements",
    "billing.edit": "Create invoices, record payments, and issue adjustments",
    "billing.collect_payment": "Initiate and process client payments (e.g., M-Pesa STK push)",
    "finance.view": "View general ledger, chart of accounts and trial balance",
    "finance.edit": "Create journal entries, vouchers and supplier invoices",
    "finance.approve": "Approve financial vouchers, expenses and write-offs",
    "finance.configure": "Configure fiscal periods and account mappings",
    "finance.reports": "Generate financial statements (P&L, Balance Sheet)",
    "finance.reconcile": "Reconcile payments and bank/M-Pesa statements",
    "finance.close_period": "Lock and close accounting fiscal periods",
    "finance.export": "Export financial reports and data",
    # Inventory, Staff & Compliance
    "inventory.view": "View general stores items and stock counts",
    "inventory.edit": "Create purchase requisitions, POs and stock issues",
    "staff.view": "View staff profiles, credentials and shift rosters",
    "staff.edit": "Manage staff profiles, leave requests and shift schedules",
    "compliance.view": "View statutory registers, licences and inspection reports",
    "compliance.edit": "Manage statutory compliance records and expiry dates",
    # Privacy & Data Protection
    "privacy.view": "View data subject requests and privacy registers",
    "privacy.manage": "Manage privacy consents and subject requests",
    "privacy.dpo": "Data Protection Officer administrative actions",
}

ADMIN_PERMISSIONS = [
    "users.manage",
    "roles.manage",
    "departments.manage",
    "settings.manage",
    "audit.view",
    "system.view",
    "privacy.view",
    "privacy.manage",
    "privacy.dpo",
]

DOCTOR_PERMISSIONS = [
    "client.view", "client.update", "referral.view", "screening.view", "screening.create",
    "admission.view", "consent.view", "assessment.view", "assessment.record", "risk.view", "risk.record",
    "clinical.view", "clinical.edit", "clinical.create_note", "clinical.record_vitals", "clinical.manage_orders",
    "lab.view", "lab.order", "lab.result", "medication.view", "medication.prescribe",
    "discharge.view", "discharge.edit", "residential.view", "safeguarding.view"
]

COUNSELLOR_PERMISSIONS = [
    "client.view", "admission.view", "consent.view", "assessment.view", "assessment.record", "assessment.configure",
    "risk.view", "risk.record", "treatment_plan.view", "treatment_plan.manage", "treatment_plan.record", "treatment_plan.review",
    "case_management.view", "programme.view", "programme.manage", "therapy.view", "therapy.create_note",
    "psychotherapy.view", "psychotherapy.create_note", "family.view", "family.record",
    "discharge.view", "residential.view", "safeguarding.view", "safeguarding.edit"
]

NURSE_PERMISSIONS = [
    "client.view", "admission.view", "consent.view", "nursing.view", "nursing.record",
    "clinical.view", "clinical.record_vitals", "medication.view", "medication.administer", "lab.view", "lab.result",
    "residential.view", "safeguarding.view", "safeguarding.edit"
]

PHARMACIST_PERMISSIONS = [
    "client.view", "medication.view", "pharmacy.view", "pharmacy.manage", "pharmacy.dispense"
]

RECEPTION_PERMISSIONS = [
    "client.view", "client.create", "client.update", "referral.view", "referral.create",
    "referral.update", "screening.view", "screening.create", "admission.view", "admission.create",
    "admission.update", "admission.assign", "admission.property", "consent.view", "consent.create",
    "residential.view", "residential.edit", "residential.assign"
]

FINANCE_PERMISSIONS = [
    "client.view", "admission.view", "billing.view", "billing.edit", "billing.collect_payment",
    "finance.view", "finance.edit", "finance.approve", "finance.configure", "finance.reports",
    "finance.reconcile", "finance.close_period", "finance.export"
]

SYSTEM_INTEGRATION_PERMISSIONS = [
    "billing.view", "billing.edit", "billing.collect_payment",
    "finance.view", "finance.edit", "finance.reconcile", "system.view"
]


def seed(db: Session, development: bool = False):
    """Idempotently seed the baseline facility, departments, permissions, roles, and dev users."""
    # 1. Facility
    facility = db.scalar(select(Facility).limit(1))
    if not facility:
        facility = Facility(
            name="ARS Rehabilitation Centre",
            system_name="ARS RMS",
            short_name="ARS",
            contact_email="info@ars-rehab.or.ke",
            phone="+254 700 000 000",
            address="Nairobi, Kenya",
            logo_url=None,
        )
        db.add(facility)
        db.flush()
        logger.info("Created baseline Facility: %s", facility.name)

    # 2. Departments
    dept_names = [
        ("Administration", "Executive and ICT systems administration"),
        ("Clinical", "Medical officers, psychiatrists and general health services"),
        ("Nursing", "Residential inpatient nursing and medication administration"),
        ("Counselling", "Psychological assessment, therapy and rehabilitation"),
        ("Pharmacy", "Pharmaceutical supply and dispensation"),
        ("Finance", "Billing, accounts receivable and general ledger accounting"),
        ("Residential", "Hostel operations, kitchen, housekeeping and security"),
        ("Logistics", "Procurement, stores and facilities maintenance"),
    ]
    departments = {}
    for name, desc in dept_names:
        dept = db.scalar(select(Department).where(Department.name == name))
        if not dept:
            dept = Department(name=name, description=desc, active=True)
            db.add(dept)
            db.flush()
        departments[name] = dept

    # 3. Permissions
    perm_objs = {}
    for code, description in ALL_PERMISSIONS.items():
        p = db.scalar(select(Permission).where(Permission.code == code))
        if not p:
            p = Permission(code=code, description=description)
            db.add(p)
            db.flush()
        perm_objs[code] = p

    # 4. Roles
    role_specs = [
        ("System Administrator", "ICT and User Administration", ADMIN_PERMISSIONS),
        ("Medical Officer", "Licensed Physician / Psychiatrist", DOCTOR_PERMISSIONS),
        ("Counsellor", "Addiction Counsellor / Clinical Psychologist", COUNSELLOR_PERMISSIONS),
        ("Nurse", "Nursing Officer / eMAR Administrator", NURSE_PERMISSIONS),
        ("Pharmacist", "Pharmacy Superintendent", PHARMACIST_PERMISSIONS),
        ("Receptionist", "Client Ingestion & Records Clerk", RECEPTION_PERMISSIONS),
        ("Finance Officer", "Billing & General Ledger Accountant", FINANCE_PERMISSIONS),
        ("System Integration", "Non-human integration identity for automated callbacks and background jobs", SYSTEM_INTEGRATION_PERMISSIONS),
    ]

    roles = {}
    for role_name, description, perm_codes in role_specs:
        role = db.scalar(select(Role).where(Role.name == role_name))
        if not role:
            role = Role(
                name=role_name,
                description=description,
                permissions=[perm_objs[c] for c in perm_codes if c in perm_objs],
            )
            db.add(role)
            db.flush()
        else:
            # Sync permissions
            existing_codes = {p.code for p in role.permissions}
            for c in perm_codes:
                if c in perm_objs and c not in existing_codes:
                    role.permissions.append(perm_objs[c])
            db.flush()
        roles[role_name] = role

    # 5. Reference Catalogues: Baseline Medication Routes
    from app.models.medication import MedicationRoute
    base_routes = [
        ("oral", "Oral"),
        ("iv", "Intravenous"),
        ("im", "Intramuscular"),
        ("sublingual", "Sublingual"),
        ("topical", "Topical"),
        ("inhalation", "Inhalation"),
    ]
    for r_code, r_name in base_routes:
        if not db.scalar(select(MedicationRoute).where(MedicationRoute.code == r_code)):
            db.add(MedicationRoute(code=r_code, name=r_name, active=True))
    db.flush()

    # 6. Non-human System Integration Actor
    integration_email = "system.integration@rehub.local"
    system_actor = db.scalar(select(User).where(User.email == integration_email))
    if not system_actor:
        system_actor = User(
            email=integration_email,
            full_name="System Integration Actor",
            password_hash="!NON_INTERACTIVE_DISABLED!",
            facility_id=facility.id,
            department_id=departments["Administration"].id,
            roles=[roles["System Integration"]],
            force_password_change=False,
            active=True,
        )
        db.add(system_actor)
        db.flush()
        logger.info("Created non-human System Integration Actor: %s", integration_email)

    # 6. Development Users
    if development:
        dev_accounts = [
            ("admin@example.org", "System Administrator", "Administration", "System Administrator"),
            ("doctor@example.org", "Dr. Kevin Ochieng", "Clinical", "Medical Officer"),
            ("counsellor@example.org", "Grace Wanjiku", "Counselling", "Counsellor"),
            ("nurse@example.org", "Sister Mary Atieno", "Nursing", "Nurse"),
            ("pharmacy@example.org", "David Kiprop", "Pharmacy", "Pharmacist"),
            ("reception@example.org", "Faith Mutua", "Administration", "Receptionist"),
            ("finance@example.org", "Peter Kamau", "Finance", "Finance Officer"),
        ]

        for email, full_name, dept_name, role_name in dev_accounts:
            user = db.scalar(select(User).where(User.email == email))
            if not user:
                user = User(
                    email=email,
                    full_name=full_name,
                    password_hash=password_hasher.hash("ChangeMe!2026"),
                    facility_id=facility.id,
                    department_id=departments[dept_name].id,
                    roles=[roles[role_name]],
                    force_password_change=True,
                    active=True,
                )
                db.add(user)
                db.flush()
                logger.info("Created development user: %s (%s)", email, role_name)

    db.commit()


def main():
    parser = argparse.ArgumentParser(description="Seed initial ReHUB database")
    parser.add_argument("--development", action="store_true", help="Seed default development staff accounts")
    args = parser.parse_args()

    with SessionLocal() as session:
        seed(session, development=args.development)
        print("Database seeded successfully.")


if __name__ == "__main__":
    main()

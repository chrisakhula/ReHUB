import logging
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models.identity import Facility
from app.models.billing import BillingService, Payer, PriceList

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_billing")

def seed():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    logger.info("Checking for default facility...")
    facility = db.query(Facility).first()
    if not facility:
        logger.warning("No facility found. Please run initial bootstrap first.")
        return

    logger.info("Seeding billing services...")
    services_data = [
        {"code": "CONSULT-01", "name": "Standard Consultation", "category": "CONSULTATION", "description": "Initial or follow-up psychiatric consultation"},
        {"code": "BED-01", "name": "Inpatient Bed Day", "category": "ACCOMMODATION", "description": "Daily ward accommodation and care"},
        {"code": "THERAPY-01", "name": "Group Therapy Session", "category": "THERAPY", "description": "1 hour group therapy"},
        {"code": "THERAPY-02", "name": "Individual Psychotherapy", "category": "THERAPY", "description": "1 hour individual psychotherapy"},
        {"code": "LAB-01", "name": "Standard Toxicology Screen", "category": "INVESTIGATION", "description": "Urine toxicology screen"}
    ]

    for s_data in services_data:
        svc = db.query(BillingService).filter_by(code=s_data["code"]).first()
        if not svc:
            svc = BillingService(**s_data, facility_id=facility.id)
            db.add(svc)
    db.commit()

    logger.info("Seeding payers...")
    payers_data = [
        {"name": "Private Self-Pay", "payer_type": "PRIVATE", "contact_person": "N/A", "contact_email": "", "contact_phone": "", "billing_address": ""},
        {"name": "NHIF", "payer_type": "INSURANCE", "contact_person": "NHIF Desk", "contact_email": "customercare@nhif.or.ke", "contact_phone": "0800 221 2744", "billing_address": "NHIF Building, Nairobi"}
    ]

    for p_data in payers_data:
        payer = db.query(Payer).filter_by(name=p_data["name"]).first()
        if not payer:
            payer = Payer(**p_data, facility_id=facility.id)
            db.add(payer)
    db.commit()

    logger.info("Seeding price lists...")
    # Get services
    consult = db.query(BillingService).filter_by(code="CONSULT-01").first()
    bed = db.query(BillingService).filter_by(code="BED-01").first()

    if consult and bed:
        # Check if prices exist
        existing_price = db.query(PriceList).filter_by(service_id=consult.id).first()
        if not existing_price:
            prices = [
                PriceList(facility_id=facility.id, service_id=consult.id, payer_category="PRIVATE", amount=3500.0, effective_from=date(2026, 1, 1)),
                PriceList(facility_id=facility.id, service_id=consult.id, payer_category="INSURANCE", amount=2500.0, effective_from=date(2026, 1, 1)),
                PriceList(facility_id=facility.id, service_id=bed.id, payer_category="PRIVATE", amount=8000.0, effective_from=date(2026, 1, 1)),
                PriceList(facility_id=facility.id, service_id=bed.id, payer_category="INSURANCE", amount=6500.0, effective_from=date(2026, 1, 1))
            ]
            db.add_all(prices)
            db.commit()

    logger.info("Billing seed completed successfully.")

if __name__ == "__main__":
    seed()

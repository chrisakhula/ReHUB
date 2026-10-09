import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models.rehabilitation import AssessmentInstrument
from app.models.identity import Facility

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_cssrs")

def seed():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    logger.info("Checking for C-SSRS assessment instrument...")
    existing = db.query(AssessmentInstrument).filter_by(code="C-SSRS").first()
    
    if existing:
        logger.info("C-SSRS instrument already exists. Skipping.")
        return

    logger.info("Creating C-SSRS instrument...")
    
    facility = db.query(Facility).first()
    if not facility:
        logger.error("No facility found. Please run core seeds first.")
        return
    
    cssrs = AssessmentInstrument(
        code="C-SSRS",
        name="Columbia-Suicide Severity Rating Scale (Screening Version)",
        instructions="Ask questions 1 and 2. If both are negative, proceed to question 6. If either is positive, ask questions 3, 4, and 5.",
        version=1,
        active=True,
        facility_id=facility.id,
        questions=[
            {
                "key": "q1",
                "text": "1. Have you wished you were dead or wished you could go to sleep and not wake up?",
                "options": [
                    {"value": "yes", "label": "Yes", "score": 1},
                    {"value": "no", "label": "No", "score": 0}
                ]
            },
            {
                "key": "q2",
                "text": "2. Have you actually had any thoughts of killing yourself?",
                "options": [
                    {"value": "yes", "label": "Yes", "score": 1},
                    {"value": "no", "label": "No", "score": 0}
                ]
            },
            {
                "key": "q3",
                "text": "3. Have you been thinking about how you might do this?",
                "options": [
                    {"value": "yes", "label": "Yes", "score": 1},
                    {"value": "no", "label": "No", "score": 0}
                ]
            },
            {
                "key": "q4",
                "text": "4. Have you had these thoughts and had some intention of acting on them?",
                "options": [
                    {"value": "yes", "label": "Yes", "score": 1},
                    {"value": "no", "label": "No", "score": 0}
                ]
            },
            {
                "key": "q5",
                "text": "5. Have you started to work out or worked out the details of how to kill yourself?",
                "options": [
                    {"value": "yes", "label": "Yes", "score": 1},
                    {"value": "no", "label": "No", "score": 0}
                ]
            },
            {
                "key": "q6",
                "text": "6. Have you ever done anything, started to do anything, or prepared to do anything to end your life?",
                "options": [
                    {"value": "yes", "label": "Yes", "score": 1},
                    {"value": "no", "label": "No", "score": 0}
                ]
            }
        ],
        score_bands=[
            {
                "minimum": 0,
                "maximum": 0,
                "interpretation": "Low Risk",
                "risk_level": "LOW"
            },
            {
                "minimum": 1,
                "maximum": 2,
                "interpretation": "Moderate Risk: Requires further clinical evaluation.",
                "risk_level": "MODERATE"
            },
            {
                "minimum": 3,
                "maximum": 6,
                "interpretation": "High/Critical Risk: Immediate intervention and safety planning required.",
                "risk_level": "CRITICAL"
            }
        ]
    )
    
    db.add(cssrs)
    db.commit()
    logger.info("C-SSRS instrument successfully seeded.")

if __name__ == "__main__":
    seed()

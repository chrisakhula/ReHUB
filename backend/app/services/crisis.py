import re
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from uuid import UUID
from app.models.clinical import CrisisAlert
logger = logging.getLogger("ars.crisis_scanner")

CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "want to die",
    "better off dead", "can't take this anymore", "hurt myself",
    "overdose", "cut myself", "give up on life"
]

def scan_text_for_crisis(
    text: str, 
    db: Session = None, 
    facility_id: UUID = None, 
    client_id: Optional[UUID] = None, 
    source_entity: str = "Unknown", 
    source_entity_id: str = "Unknown"
) -> List[str]:
    """
    Scans patient-entered text or clinical notes for high-risk crisis keywords.
    Returns a list of matched keywords/phrases.
    """
    if not text:
        return []
        
    text_lower = text.lower()
    matches = []
    
    for keyword in CRISIS_KEYWORDS:
        # Simple regex for whole-word/phrase boundaries, allowing some punctuation
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, text_lower):
            matches.append(keyword)
            
    if matches:
        logger.warning(f"CRITICAL: Crisis keywords detected in text: {matches}")
        if db and facility_id:
            alert = CrisisAlert(
                facility_id=facility_id,
                client_id=client_id,
                source_entity=source_entity,
                source_entity_id=source_entity_id,
                detected_keywords=", ".join(matches),
                text_snippet=text[:500],
                severity="CRITICAL",
                status="NEW"
            )
            db.add(alert)
            # Will be flushed/committed by the calling service
            
    return matches

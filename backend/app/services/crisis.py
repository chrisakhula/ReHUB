import re
import logging
from typing import List

logger = logging.getLogger("ars.crisis_scanner")

CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "want to die",
    "better off dead", "can't take this anymore", "hurt myself",
    "overdose", "cut myself", "give up on life"
]

def scan_text_for_crisis(text: str) -> List[str]:
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
        # In a real implementation, this would trigger an email or SMS to the duty clinician
        # notify_duty_clinician(matches, text)
        
    return matches

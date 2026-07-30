import re
from typing import Tuple, Optional

CRISIS_PATTERNS = [
    r'\b(kill|end)\s+(myself|my\s+life)\b',
    r'\bsuicid(e|al)\b',
    r'\bwant\s+to\s+die\b',
    r'\bself[- ]harm\b',
    r'\bcut(ting)?\s+myself\b',
    r'\bno\s+reason\s+to\s+live\b',
    r'\bbetter\s+off\s+dead\b',
    r'\bhopeless\s+and\s+want\s+to\s+end\b'
]

CRISIS_RESPONSE = "I hear that you're going through an extremely difficult time right now, and I want you to know that you don't have to carry this alone. Please reach out to someone who can support you right away.\n\nIf you are in immediate danger or feel you cannot keep yourself safe, please connect with a crisis resource immediately:\n\n- **National Suicide Prevention Lifeline / Crisis Lifeline (US/Canada):** Call or text **988** (Available 24/7, free and confidential)\n- **Crisis Text Line:** Text **HOME** to **741741**\n- **Vandrevala Foundation Helpline (India):** Call **9999 666 555** or **1860-2662-345**\n- **International Resources:** Find immediate support in your country at [findahelpline.com](https://findahelpline.com/)\n\nIf you are experiencing a medical emergency, please call your local emergency service or go to the nearest emergency room.\n\nPlease reach out to one of these services or a trusted professional. Your life matters."

from app.security.crisis_guard import crisis_guard

def check_crisis_safety(message: str) -> Tuple[bool, Optional[str]]:
    res = crisis_guard.evaluate_prompt(message)
    if res.is_crisis and res.override_message:
        return True, res.override_message
    return False, None

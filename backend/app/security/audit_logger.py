"""
Audit Logger — Production Audit Trail Recorder
Records security events, authentication attempts, document uploads,
memory deletions, rate limit triggers, and tool calls.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("audit_trail")

class AuditLogger:
    def log_event(
        self,
        event_type: str,            # 'LOGIN_SUCCESS' | 'LOGIN_FAILURE' | 'FILE_UPLOAD' | 'MEMORY_DELETED' | 'INJECTION_ATTEMPT' | 'RATE_LIMIT' | 'TOOL_CALL'
        user_id: Optional[str],
        details: Dict[str, Any],
        ip_address: Optional[str] = None
    ):
        timestamp = datetime.utcnow().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "user_id": user_id or "anonymous",
            "ip_address": ip_address or "internal",
            "details": details
        }
        logger.info(f"[AUDIT] {event_type} | User: {user_id} | {details}")
        print(f"🛡️ [AUDIT LOG {timestamp[:19]}] {event_type} | User: {user_id} | {details}", flush=True)

audit_logger = AuditLogger()

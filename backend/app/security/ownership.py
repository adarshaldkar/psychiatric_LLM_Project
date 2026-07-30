"""
Resource Ownership Security Validator
Enforces strict resource isolation across users:
- conversation.user_id == current_user.id
- document.user_id == current_user.id
- memory.user_id == current_user.id
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.models import Conversation, Document, LongTermMemory

class ResourceOwnershipValidator:
    def verify_conversation_owner(self, conversation_id: str, user_id: str, db: Session) -> Conversation:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
        if str(conv.user_id) != str(user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You do not own this conversation.")
        return conv

    def verify_document_owner(self, document_id: str, user_id: str, db: Session) -> Document:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
        if not doc.is_global and str(doc.user_id) != str(user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You do not own this document.")
        return doc

    def verify_memory_owner(self, memory_id: str, user_id: str, db: Session) -> LongTermMemory:
        mem = db.query(LongTermMemory).filter(LongTermMemory.id == memory_id).first()
        if not mem:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory item not found.")
        if str(mem.user_id) != str(user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You do not own this memory item.")
        return mem

ownership_validator = ResourceOwnershipValidator()

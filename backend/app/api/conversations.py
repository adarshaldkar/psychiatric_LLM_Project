from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.core.database import get_db
from app.models.models import User, Conversation, Message
from app.schemas.schemas import ConversationResponse, ConversationDetailResponse, ConversationCreate
from app.api.auth import get_current_user

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("", response_model=List[ConversationResponse])
def list_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id, Conversation.is_archived == False)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    res = []
    for c in convs:
        c_res = ConversationResponse.model_validate(c)
        c_res.message_count = len(c.messages)
        res.append(c_res)
    return res

@router.post("", response_model=ConversationResponse)
def create_conversation(conv_in: ConversationCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = Conversation(
        user_id=current_user.id,
        title=conv_in.title or "New Conversation"
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ConversationResponse.model_validate(conv)

@router.get("/{conv_id}", response_model=ConversationDetailResponse)
def get_conversation(conv_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetailResponse.model_validate(conv)

@router.delete("/{conv_id}")
def delete_conversation(conv_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return {"message": "Conversation deleted successfully"}

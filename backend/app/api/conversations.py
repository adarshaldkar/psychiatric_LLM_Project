from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from app.core.database import get_db
from app.models.models import User, Conversation, Message
from app.schemas.schemas import ConversationResponse, ConversationDetailResponse, ConversationCreate
from app.api.auth import get_current_user

router = APIRouter(prefix="/conversations", tags=["Conversations"])


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    is_archived: Optional[bool] = None

@router.get("", response_model=List[ConversationResponse])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100, description="Number of conversations per page"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    archived: bool = Query(default=False, description="Include archived conversations"),
):
    """List user conversations with pagination. Default page size: 20."""
    query = (
        db.query(Conversation)
        .filter(
            Conversation.user_id == current_user.id,
            Conversation.is_archived == archived
        )
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    convs = query.all()
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

@router.patch("/{conv_id}", response_model=ConversationResponse)
def update_conversation(
    conv_id: UUID,
    update_in: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update conversation title or archive status."""
    conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if update_in.title is not None:
        conv.title = update_in.title[:100]  # cap title length
    if update_in.is_archived is not None:
        conv.is_archived = update_in.is_archived
    db.commit()
    db.refresh(conv)
    return ConversationResponse.model_validate(conv)


@router.delete("/{conv_id}")
def delete_conversation(conv_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return {"message": "Conversation deleted successfully"}

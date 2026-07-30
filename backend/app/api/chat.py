from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import User, Conversation, Message
from app.schemas.schemas import MessageCreate
from app.api.auth import get_current_user
from app.orchestrator.orchestrator import orchestrator

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/message")
async def send_chat_message(
    msg_in: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not msg_in.conversation_id:
        conv = Conversation(user_id=current_user.id, title=msg_in.content[:30] + "...")
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id
    else:
        conv = db.query(Conversation).filter(Conversation.id == msg_in.conversation_id, Conversation.user_id == current_user.id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conv_id = conv.id

    if conv.title == "New Conversation":
        conv.title = msg_in.content[:35] + ("..." if len(msg_in.content) > 35 else "")
        db.commit()

    user_msg = Message(
        conversation_id=conv_id,
        role="user",
        content=msg_in.content
    )
    db.add(user_msg)
    db.commit()

    return StreamingResponse(
        orchestrator.process_chat_message(
            user_message=msg_in.content,
            conversation_id=str(conv_id),
            user_id=str(current_user.id),
            db=db
        ),
        media_type="text/event-stream"
    )

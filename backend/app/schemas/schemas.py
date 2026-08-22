from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any, Dict
from datetime import datetime
from uuid import UUID

# Auth Schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime
    is_guest: bool = False
    
    class Config:
        from_attributes = True

    @classmethod
    def from_orm_user(cls, user: Any) -> "UserResponse":
        is_guest = bool((user.preferences or {}).get("is_guest", False)) if hasattr(user, "preferences") else False
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            created_at=user.created_at,
            is_guest=is_guest
        )

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    user: UserResponse

# Message Schemas
class MessageCreate(BaseModel):
    conversation_id: Optional[UUID] = None
    content: str

class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime
    metadata_info: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

# Conversation Schemas
class ConversationCreate(BaseModel):
    title: Optional[str] = 'New Conversation'

class ConversationResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    summary: Optional[str] = None
    message_count: Optional[int] = 0

    class Config:
        from_attributes = True

class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse] = []

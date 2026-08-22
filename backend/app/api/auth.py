import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import User
from app.schemas.schemas import UserRegister, UserLogin, TokenResponse, UserResponse
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from fastapi.security import OAuth2PasswordBearer
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Password policy constants
_MIN_PASSWORD_LEN = 8
_MAX_PASSWORD_LEN = 128  # Prevents bcrypt DoS (bcrypt truncates at 72, huge inputs are wasteful)
_MAX_EMAIL_LEN = 255

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

@router.post("/guest", response_model=TokenResponse)
def create_guest(db: Session = Depends(get_db)):
    """
    Creates an anonymous guest user account for immediate, friction-free AI exploration.
    Allows visitors to chat and test MindCare AI without upfront login barriers.
    """
    guest_uid = uuid.uuid4().hex[:12]
    guest_email = f"guest_{guest_uid}@guest.mindcare.ai"
    guest_pw = uuid.uuid4().hex
    
    user = User(
        email=guest_email,
        password_hash=hash_password(guest_pw),
        full_name="Guest Visitor",
        preferences={"is_guest": True, "created_as": "trial"}
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, user=UserResponse.from_orm_user(user))

@router.post("/register", response_model=TokenResponse)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    # ── Input validation ────────────────────────────────────────────────────
    if len(user_in.email) > _MAX_EMAIL_LEN:
        raise HTTPException(status_code=400, detail="Email address too long")
    if len(user_in.password) < _MIN_PASSWORD_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {_MIN_PASSWORD_LEN} characters"
        )
    if len(user_in.password) > _MAX_PASSWORD_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Password must not exceed {_MAX_PASSWORD_LEN} characters"
        )
    if len(user_in.password) > 72:
        logger.warning(
            f"Register: password exceeds 72 chars — bcrypt will silently truncate. "
            f"User email: {user_in.email[:20]}..."
        )

    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        full_name=user_in.full_name,
        preferences={"is_guest": False}
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, user=UserResponse.from_orm_user(user))

@router.post("/login", response_model=TokenResponse)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, user=UserResponse.from_orm_user(user))

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.from_orm_user(current_user)

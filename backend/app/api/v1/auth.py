import uuid
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import jwt
from pydantic import BaseModel, EmailStr

from app.db.session import get_db
from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.repositories.user import UserRepository
from app.schemas.user import UserResponse, UserCreate
from app.schemas.token import Token
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SetupRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str

class SetupStatusResponse(BaseModel):
    has_agm: bool

class AGMStatusResponse(BaseModel):
    agm_exists: bool

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    token: str
    new_password: str

class RefreshRequest(BaseModel):
    refresh_token: str

def send_reset_email(to_email: str, reset_token: str) -> bool:
    """Send reset code email using SMTP."""
    # Check if SMTP configuration is set up
    if not all([settings.SMTP_HOST, settings.SMTP_USER, settings.SMTP_PASSWORD, settings.SMTP_FROM_EMAIL]):
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = "Pothys AGM AI Assistant - Password Reset Code"
        
        # Link for Expo Web
        link = f"http://localhost:8081/?email={to_email}&token={reset_token}"
        
        body = (
            f"Dear AGM Executive,\n\n"
            f"A password reset request was initiated for your account.\n\n"
            f"To reset your password, click the link below:\n"
            f"{link}\n\n"
            f"Alternatively, enter this secure verification reset code on the reset screen:\n"
            f"{reset_token}\n\n"
            f"This code will expire in 15 minutes.\n\n"
            f"If you did not request this, please contact the system administrator immediately.\n\n"
            f"Sincerely,\n"
            f"Pothys Enterprise Systems"
        )
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to server
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())
        server.close()
        return True
    except Exception as e:
        print(f"Error sending SMTP email: {e}")
        return False

@router.post("/login", response_model=Token)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate AGM/Manager credentials and return security tokens."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    return Token(access_token=access_token, refresh_token=refresh_token)

@router.get("/setup-status", response_model=SetupStatusResponse)
async def setup_status(db: AsyncSession = Depends(get_db)):
    """Check if any AGM executive account is already configured in the database."""
    user_repo = UserRepository(db)
    has_agm = await user_repo.check_agm_exists()
    return SetupStatusResponse(has_agm=has_agm)

@router.get("/agm-status", response_model=AGMStatusResponse)
async def agm_status(db: AsyncSession = Depends(get_db)):
    """Check if an AGM account exists in PostgreSQL."""
    user_repo = UserRepository(db)
    agm_exists = await user_repo.check_agm_exists()
    return AGMStatusResponse(agm_exists=agm_exists)

@router.post("/setup", response_model=Token)
async def setup_executive(payload: SetupRequest, db: AsyncSession = Depends(get_db)):
    """Configure the initial single AGM executive account. Allowed only once."""
    user_repo = UserRepository(db)
    exists = await user_repo.check_agm_exists()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Executive account already exists."
        )
    
    # Validate email uniqueness
    existing_user = await user_repo.get_by_email(payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address already registered."
        )
        
    # Validate password strength
    password = payload.password
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long."
        )
    if not any(char.isdigit() for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one number."
        )
    if not any(char.isalpha() for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one letter."
        )
    
    user_in = UserCreate(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        role="AGM",
        branch_id=None
    )
    user = await user_repo.create(user_in)
    
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    return Token(access_token=access_token, refresh_token=refresh_token)

@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Initiate password reset flow. Generates reset token and sends email."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(payload.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Corporate email not registered."
        )
        
    token = "".join(secrets.choice("0123456789") for _ in range(6))
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    user.reset_token = token
    user.reset_token_expires = expires
    await db.commit()
    
    email_sent = send_reset_email(payload.email, token)
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset service is unavailable. Please contact the system administrator."
        )
        
    return {"detail": "Password reset code sent to your corporate email."}

@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Reset password using valid reset token."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(payload.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
        
    if not user.reset_token or user.reset_token != payload.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or incorrect reset token."
        )
        
    expires = user.reset_token_expires
    if expires:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired."
            )
            
    user.password_hash = get_password_hash(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    await db.commit()
    
    return {"detail": "Password reset successful. You can now login with your new credentials."}

@router.post("/refresh", response_model=Token)
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh JWT access token using a valid refresh token."""
    try:
        payload_data = jwt.decode(
            payload.refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        if not payload_data.get("refresh"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token")
        user_id_str = payload_data.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token")
        user_id = uuid.UUID(user_id_str)
    except (jwt.JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    access_token = create_access_token(subject=user.id)
    new_refresh_token = create_refresh_token(subject=user.id)
    return Token(access_token=access_token, refresh_token=new_refresh_token)

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve details of the currently authenticated session owner."""
    return current_user

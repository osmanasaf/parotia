from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.services.user_service import UserService
from app.core.auth import create_access_token, get_current_user
from app.core.exceptions import BaseAppException
from app.core.config import get_settings
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["authentication"])

def handle_exception(e: Exception) -> HTTPException:
    """Handle exceptions and convert to HTTPException"""
    if isinstance(e, BaseAppException):
        return HTTPException(
            status_code=e.status_code,
            detail=e.message
        )
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred"
        )

@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        user_service = UserService(db)
        user = user_service.create_user(user_data)
        return user
    except Exception as e:
        raise handle_exception(e)

@router.post("/send-verification")
def send_verification_email(email: str, db: Session = Depends(get_db)):
    """Send verification email to user"""
    try:
        user_service = UserService(db)
        verification_code = user_service.send_verification_email(email)
        
        return {
            "message": "Verification email sent successfully",
            "verification_code": verification_code  # Development için response'da döndürüyoruz
        }
        
    except Exception as e:
        raise handle_exception(e)

@router.post("/verify-email")
def verify_email(email: str, code: str, db: Session = Depends(get_db)):
    """Verify user email with email and code"""
    try:
        user_service = UserService(db)
        user = user_service.verify_email_with_email(email, code)
        return {
            "message": "Email verified successfully!",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "is_verified": user.is_verified
            }
        }
    except Exception as e:
        raise handle_exception(e)

@router.post("/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user and return access token"""
    try:
        user_service = UserService(db)
        user = user_service.authenticate_user(user_credentials.email, user_credentials.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please verify your email before logging in"
            )
        
        # Create access token
        settings = get_settings()
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except Exception as e:
        raise handle_exception(e)

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user information"""
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_id(current_user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user
        
    except Exception as e:
        raise handle_exception(e) 
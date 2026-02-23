from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token, UserUpdate, PasswordChange, EmailChangeRequest, EmailChangeConfirm, PasswordResetRequest, PasswordResetConfirm, UserNameUpdate
from app.services.user_service import UserService
from app.core.auth import create_access_token, create_refresh_token, get_current_user
from app.core.exceptions import BaseAppException, EmailNotVerifiedException, InvalidCredentialsException
from app.core.config import get_settings
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["authentication"])

def handle_exception(e: Exception) -> HTTPException:
    """Handle exceptions and convert to HTTPException"""
    if isinstance(e, BaseAppException):
        # Özel exception'lar için detaylı response
        if hasattr(e, 'to_dict'):
            error_data = e.to_dict()
            return HTTPException(
                status_code=e.status_code,
                detail=error_data
            )
        else:
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
            raise InvalidCredentialsException(
                message="Email veya şifre hatalı"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        if not user.is_verified:
            raise EmailNotVerifiedException(
                message="Lütfen giriş yapmadan önce email adresinizi doğrulayın"
            )
        
        # Create access token
        settings = get_settings()
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        # Create refresh token
        refresh_token, refresh_token_expires = create_refresh_token(
            data={"sub": str(user.id)}
        )
        user_service.store_refresh_token(user.id, refresh_token, refresh_token_expires)
        
        return {
            "access_token": access_token, 
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
        
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

@router.put("/me", response_model=UserResponse)
def update_current_user(
    update_data: UserNameUpdate,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's name fields (first_name, last_name)"""
    try:
        user_service = UserService(db)
        updated_user = user_service.update_user_name(current_user_id, update_data)
        return updated_user
    except Exception as e:
        raise handle_exception(e)

@router.post("/change-password")
def change_password(
    payload: PasswordChange,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change current user's password"""
    try:
        user_service = UserService(db)
        user_service.change_password(current_user_id, payload.current_password, payload.new_password)
        return {"message": "Şifre başarıyla güncellendi"}
    except Exception as e:
        raise handle_exception(e)

@router.post("/request-email-change")
def request_email_change(
    payload: EmailChangeRequest,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """İki aşamalı email değişimi: 1) yeni emaile kod gönder"""
    try:
        user_service = UserService(db)
        user_service.request_email_change(current_user_id, payload.new_email)
        return {"message": "Doğrulama kodu yeni e‑posta adresine gönderildi"}
    except Exception as e:
        raise handle_exception(e)

@router.post("/confirm-email-change", response_model=UserResponse)
def confirm_email_change(
    payload: EmailChangeConfirm,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """İki aşamalı email değişimi: 2) kodu doğrula ve email’i kalıcı olarak güncelle"""
    try:
        user_service = UserService(db)
        updated = user_service.confirm_email_change(current_user_id, payload.new_email, payload.code)
        return updated
    except Exception as e:
        raise handle_exception(e)

@router.post("/request-password-reset")
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    """Şifre sıfırlama kodu gönder"""
    try:
        user_service = UserService(db)
        user_service.request_password_reset(payload.email)
        return {"message": "Şifre sıfırlama kodu email adresinize gönderildi"}
    except Exception as e:
        raise handle_exception(e)

@router.post("/confirm-password-reset")
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Kodu doğrula ve yeni şifreyi ayarla"""
    try:
        user_service = UserService(db)
        user_service.confirm_password_reset(payload.email, payload.code, payload.new_password)
        return {"message": "Şifreniz başarıyla sıfırlandı"}
    except Exception as e:
        raise handle_exception(e)

@router.post("/refresh", response_model=Token)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Refresh access token using a refresh token"""
    try:
        user_service = UserService(db)
        user_id = user_service.verify_refresh_token(refresh_token)
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create new access token
        settings = get_settings()
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(
            data={"sub": str(user_id)}, expires_delta=access_token_expires
        )
        
        # Create new refresh token (rotation)
        new_refresh_token, refresh_token_expires = create_refresh_token(
            data={"sub": str(user_id)}
        )
        user_service.store_refresh_token(user_id, new_refresh_token, refresh_token_expires)
        
        return {
            "access_token": new_access_token, 
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
    except Exception as e:
        raise handle_exception(e)

@router.post("/logout")
def logout(refresh_token: str, db: Session = Depends(get_db)):
    """Logout user and invalidate refresh token"""
    try:
        user_service = UserService(db)
        user_service.revoke_refresh_token(refresh_token)
        return {"message": "Successfully logged out"}
    except Exception as e:
        raise handle_exception(e)
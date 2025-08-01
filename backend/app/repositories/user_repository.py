from typing import Optional
from sqlalchemy.orm import Session
from app.repositories.base_repository import BaseRepository
from app.models.user import User, EmailVerification
from app.core.exceptions import UserNotFoundException

class UserRepository(BaseRepository[User]):
    """User repository with user-specific operations"""
    
    def __init__(self, db: Session):
        super().__init__(User, db)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.filter_one_by(email=email)
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.filter_one_by(username=username)
    
    def email_exists(self, email: str) -> bool:
        """Check if email exists"""
        return self.exists(email=email)
    
    def username_exists(self, username: str) -> bool:
        """Check if username exists"""
        return self.exists(username=username)
    
    def create_user(self, email: str, username: str, hashed_password: str) -> User:
        """Create new user"""
        return self.create({
            "email": email,
            "username": username,
            "hashed_password": hashed_password,
            "is_active": True,
            "is_verified": False
        })
    
    def update_verification_status(self, user_id: int, is_verified: bool) -> User:
        """Update user verification status"""
        user = self.get(user_id)
        if not user:
            raise UserNotFoundException(f"User with ID {user_id} not found")
        
        return self.update(user, {"is_verified": is_verified})

class EmailVerificationRepository(BaseRepository[EmailVerification]):
    """Email verification repository"""
    
    def __init__(self, db: Session):
        super().__init__(EmailVerification, db)
    
    def create_verification(self, user_id: int, verification_code: str, expires_at) -> EmailVerification:
        """Create verification record"""
        return self.create({
            "user_id": user_id,
            "verification_code": verification_code,
            "expires_at": expires_at,
            "is_used": False
        })
    
    def get_valid_verification(self, user_id: int, code: str, current_time) -> Optional[EmailVerification]:
        """Get valid verification record"""
        return self.db.query(EmailVerification).filter(
            EmailVerification.user_id == user_id,
            EmailVerification.verification_code == code,
            EmailVerification.is_used == False,
            EmailVerification.expires_at > current_time
        ).first()
    
    def mark_as_used(self, verification_id: int) -> bool:
        """Mark verification as used"""
        verification = self.get(verification_id)
        if verification:
            self.update(verification, {"is_used": True})
            return True
        return False 
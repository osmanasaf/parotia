import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate
from app.core.auth import get_password_hash, verify_password
from app.core.exceptions import (
    UserNotFoundException, UserAlreadyExistsException, 
    InvalidCredentialsException, EmailNotVerifiedException
)
from app.repositories.user_repository import UserRepository, EmailVerificationRepository
from app.services.email_service import EmailService
from app.models.user import User

logger = logging.getLogger(__name__)

class UserService:
    """User service with dependency injection and better separation of concerns"""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repository = UserRepository(db)
        self.verification_repository = EmailVerificationRepository(db)
        self.email_service = EmailService(verification_repository=self.verification_repository)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.user_repository.get_by_email(email)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.user_repository.get_by_username(username)
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.user_repository.get(user_id)
    
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user"""
        try:
            logger.info(f"Creating user with email: {user_data.email}")
            
            # Check if email already exists
            if self.user_repository.email_exists(user_data.email):
                raise UserAlreadyExistsException("Email already registered")
            
            # Check if username already exists
            if self.user_repository.username_exists(user_data.username):
                raise UserAlreadyExistsException("Username already taken")
            
            # Hash password
            hashed_password = get_password_hash(user_data.password)
            logger.info("Password hashed successfully")
            
            # Create user
            user = self.user_repository.create_user(
                email=user_data.email,
                username=user_data.username,
                hashed_password=hashed_password
            )
            
            logger.info(f"User created successfully with ID: {user.id}")
            return user
            
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            self.db.rollback()
            raise
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = self.get_user_by_email(email)
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        return user
    
    def update_user_verification(self, user_id: int, is_verified: bool = True) -> User:
        """Update user verification status"""
        return self.user_repository.update_verification_status(user_id, is_verified)
    
    def send_verification_email(self, email: str) -> str:
        """Send verification email and return code"""
        user = self.get_user_by_email(email)
        if not user:
            raise UserNotFoundException("User not found with this email")
        
        if user.is_verified:
            raise EmailNotVerifiedException("Email is already verified")
        
        # Create verification code and send email
        verification_code = self.email_service.create_verification_record(user.id)
        self.email_service.send_verification_email(
            user_email=user.email,
            username=user.username,
            verification_code=verification_code
        )
        
        return verification_code
    
    def verify_email_with_email(self, email: str, code: str) -> User:
        """Verify user email with email and code"""
        # First check if user exists with this email
        user = self.get_user_by_email(email)
        if not user:
            raise UserNotFoundException("User not found with this email")
        
        if user.is_verified:
            raise EmailNotVerifiedException("Email is already verified")
        
        # Verify the code
        self.email_service.verify_code(user.id, code)
        
        # Update user verification status
        return self.update_user_verification(user.id, True) 
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserUpdate, UserNameUpdate
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
                hashed_password=hashed_password,
                first_name=user_data.first_name,
                last_name=user_data.last_name
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
        
        # Create verification code bound to current email and send email
        verification_code = self.email_service.create_verification_record(user.id, target_email=user.email)
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
        
        # Verify the code strictly for this purpose and target email
        self.email_service.verify_code(user.id, code, purpose="verify_email", target_email=user.email)
        
        # Update user verification status
        return self.update_user_verification(user.id, True) 

    def update_user(self, user_id: int, update_data: UserUpdate) -> User:
        """Update user profile fields (username, first_name, last_name).
        Email değişimi bu metotta yapılmaz; iki aşamalı akış kullanılır.
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundException("User not found")

        fields_to_update = {}

        # Email alanı bu akışta güncellenmez
        if update_data.email and update_data.email != user.email:
            raise UserAlreadyExistsException("Email değişimi için lütfen email değişim akışını kullanın")

        if update_data.username and update_data.username != user.username:
            if self.user_repository.username_exists(update_data.username):
                raise UserAlreadyExistsException("Username already taken")
            fields_to_update["username"] = update_data.username

        if update_data.first_name is not None:
            fields_to_update["first_name"] = update_data.first_name

        if update_data.last_name is not None:
            fields_to_update["last_name"] = update_data.last_name

        if not fields_to_update:
            return user

        updated_user = self.user_repository.update_user_fields(user, fields_to_update)

        return updated_user

    def update_user_name(self, user_id: int, update_data: UserNameUpdate) -> User:
        """Sadece first_name ve last_name günceller"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundException("User not found")
        fields_to_update = {}
        if update_data.first_name is not None:
            fields_to_update["first_name"] = update_data.first_name
        if update_data.last_name is not None:
            fields_to_update["last_name"] = update_data.last_name
        if not fields_to_update:
            return user
        return self.user_repository.update_user_fields(user, fields_to_update)

    def request_email_change(self, user_id: int, new_email: str) -> bool:
        """Start email change flow: check uniqueness and send code to new email"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundException("User not found")
        if self.user_repository.email_exists(new_email):
            raise UserAlreadyExistsException("Email already registered")
        code = self.email_service.create_email_change_record(user_id, new_email)
        self.email_service.send_email_change_verification(new_email, user.username, code)
        return True

    def confirm_email_change(self, user_id: int, new_email: str, code: str) -> User:
        """Confirm email change with code and persist email"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundException("User not found")
        # Verify code bound to purpose and target email
        self.email_service.verify_code(user_id, code, purpose="email_change", target_email=new_email)
        # Persist new email as verified
        updated = self.user_repository.update_user_fields(user, {"email": new_email, "is_verified": True})
        return updated

    def request_password_reset(self, email: str) -> bool:
        """Start password reset flow by sending a code to user's email"""
        user = self.get_user_by_email(email)
        if not user:
            # Güvenlik için true dönebiliriz; ama burada açıkça söyleyelim
            raise UserNotFoundException("User not found with this email")
        code = self.email_service.create_password_reset_record(user.id, target_email=user.email)
        self.email_service.send_password_reset_email(user.email, user.username, code)
        return True

    def confirm_password_reset(self, email: str, code: str, new_password: str) -> bool:
        """Confirm password reset with code and set new password"""
        user = self.get_user_by_email(email)
        if not user:
            raise UserNotFoundException("User not found with this email")
        self.email_service.verify_code(user.id, code, purpose="password_reset", target_email=user.email)
        new_hashed = get_password_hash(new_password)
        # is_verified değerini koru
        self.user_repository.update_user_fields(user, {"hashed_password": new_hashed, "is_verified": user.is_verified})
        return True

    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """Change user password after verifying current password"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundException("User not found")

        if not verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsException("Mevcut şifre hatalı")

        new_hashed = get_password_hash(new_password)
        # is_verified değerini koru
        self.user_repository.update_user_fields(user, {"hashed_password": new_hashed, "is_verified": user.is_verified})
        return True
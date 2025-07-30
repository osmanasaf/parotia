import random
from datetime import datetime, timedelta
from typing import Optional
from app.core.config import get_settings
from app.core.exceptions import EmailServiceException, VerificationCodeExpiredException, InvalidVerificationCodeException
from app.services.email.email_service_factory import EmailServiceFactory
from app.repositories.user_repository import EmailVerificationRepository

class EmailService:
    """Email service with dependency injection and better separation of concerns"""
    
    def __init__(self, email_sender=None, verification_repository=None):
        self.settings = get_settings()
        self.email_sender = email_sender or EmailServiceFactory.create_email_sender()
        self.verification_repository = verification_repository
    
    def send_verification_email(self, user_email: str, username: str, verification_code: str) -> bool:
        """Send verification email to user"""
        try:
            subject = "Email Verification Code - Parotia"
            body = self._create_verification_email_body(username, verification_code)
            
            success = self.email_sender.send_email(
                to_email=user_email,
                subject=subject,
                body=body,
                verification_code=verification_code
            )
            
            if not success:
                raise EmailServiceException("Failed to send verification email")
            
            return True
            
        except Exception as e:
            raise EmailServiceException(f"Error sending verification email: {str(e)}")
    
    def generate_verification_code(self) -> str:
        """Generate a 6-digit verification code"""
        return str(random.randint(100000, 999999))
    
    def create_verification_record(self, user_id: int) -> str:
        """Create verification record and return code"""
        if not self.verification_repository:
            raise EmailServiceException("Verification repository not initialized")
        
        code = self.generate_verification_code()
        expires_at = datetime.utcnow() + timedelta(minutes=self.settings.VERIFICATION_CODE_EXPIRE_MINUTES)
        
        self.verification_repository.create_verification(user_id, code, expires_at)
        return code
    
    def verify_code(self, user_id: int, code: str) -> bool:
        """Verify email verification code"""
        if not self.verification_repository:
            raise EmailServiceException("Verification repository not initialized")
        
        current_time = datetime.utcnow()
        verification = self.verification_repository.get_valid_verification(user_id, code, current_time)
        
        if not verification:
            raise InvalidVerificationCodeException("Invalid or expired verification code")
        
        # Mark as used
        self.verification_repository.mark_as_used(verification.id)
        return True
    
    def _create_verification_email_body(self, username: str, verification_code: str) -> str:
        """Create HTML email body"""
        return f"""
        <html>
        <body>
            <h2>Welcome to Parotia, {username}!</h2>
            <p>Thank you for registering. Please verify your email address using the verification code below:</p>
            <div style="background-color: #f4f4f4; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                <h1 style="color: #333; font-size: 32px; letter-spacing: 8px; margin: 0;">{verification_code}</h1>
            </div>
            <p>This code will expire in {self.settings.VERIFICATION_CODE_EXPIRE_MINUTES} minutes.</p>
            <p>If you didn't create an account, please ignore this email.</p>
            <br>
            <p>Best regards,<br>The Parotia Team</p>
        </body>
        </html>
        """ 
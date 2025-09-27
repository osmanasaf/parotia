import random
from datetime import datetime, timedelta, timezone
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
        self._ERR_REPO_NOT_INITIALIZED = "Verification repository not initialized"
    
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
    
    def create_verification_record(self, user_id: int, *, target_email: Optional[str] = None) -> str:
        """Create verification record and return code. Optionally binds target_email for stricter verification."""
        if not self.verification_repository:
            raise EmailServiceException(self._ERR_REPO_NOT_INITIALIZED)
        
        code = self.generate_verification_code()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.settings.VERIFICATION_CODE_EXPIRE_MINUTES)
        
        self.verification_repository.create_verification(
            user_id,
            code,
            expires_at,
            purpose="verify_email",
            target_email=target_email,
        )
        return code
    
    def verify_code(self, user_id: int, code: str, *, purpose: Optional[str] = "verify_email", target_email: Optional[str] = None) -> bool:
        """Doğrulama kodunu amaca ve (gerekirse) hedef emaile göre doğrular"""
        if not self.verification_repository:
            raise EmailServiceException(self._ERR_REPO_NOT_INITIALIZED)

        current_time = datetime.now(timezone.utc)
        verification = self.verification_repository.get_valid_verification(
            user_id,
            code,
            current_time,
            purpose=purpose,
            target_email=target_email,
        )

        if not verification:
            raise InvalidVerificationCodeException("Invalid or expired verification code")

        self.verification_repository.mark_as_used(verification.id)
        return True

    def create_email_change_record(self, user_id: int, new_email: str) -> str:
        """E‑posta değişimi için doğrulama kaydı oluşturur ve kodu döner"""
        if not self.verification_repository:
            raise EmailServiceException(self._ERR_REPO_NOT_INITIALIZED)

        code = self.generate_verification_code()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.settings.VERIFICATION_CODE_EXPIRE_MINUTES)

        self.verification_repository.create_verification(
            user_id,
            code,
            expires_at,
            purpose="email_change",
            target_email=new_email,
        )
        return code

    def send_email_change_verification(self, new_email: str, username: str, verification_code: str) -> bool:
        """E‑posta değişimi için doğrulama e‑postası gönderir"""
        try:
            subject = "Email Change Verification Code - Parotia"
            body = self._create_email_change_email_body(username, verification_code, new_email)

            success = self.email_sender.send_email(
                to_email=new_email,
                subject=subject,
                body=body,
                verification_code=verification_code,
            )

            if not success:
                raise EmailServiceException("Failed to send email change verification email")

            return True
        except Exception as e:
            raise EmailServiceException(f"Error sending email change verification: {str(e)}")

    def create_password_reset_record(self, user_id: int, *, target_email: Optional[str] = None) -> str:
        """Şifre sıfırlama için doğrulama kaydı oluşturur ve kodu döner. target_email ile bağlar."""
        if not self.verification_repository:
            raise EmailServiceException(self._ERR_REPO_NOT_INITIALIZED)

        code = self.generate_verification_code()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.settings.VERIFICATION_CODE_EXPIRE_MINUTES)

        self.verification_repository.create_verification(
            user_id,
            code,
            expires_at,
            purpose="password_reset",
            target_email=target_email,
        )
        return code

    def send_password_reset_email(self, user_email: str, username: str, verification_code: str) -> bool:
        """Şifre sıfırlama kodunu içeren e‑postayı gönderir"""
        try:
            subject = "Password Reset Code - Parotia"
            body = self._create_password_reset_email_body(username, verification_code)

            success = self.email_sender.send_email(
                to_email=user_email,
                subject=subject,
                body=body,
                verification_code=verification_code,
            )

            if not success:
                raise EmailServiceException("Failed to send password reset email")

            return True
        except Exception as e:
            raise EmailServiceException(f"Error sending password reset email: {str(e)}")
    
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

    def _create_email_change_email_body(self, username: str, verification_code: str, new_email: str) -> str:
        return f"""
        <html>
        <body>
            <h2>Hello {username},</h2>
            <p>We received a request to change your email to <b>{new_email}</b>. Use the verification code below to confirm this change:</p>
            <div style=\"background-color: #f4f4f4; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;\">
                <h1 style=\"color: #333; font-size: 32px; letter-spacing: 8px; margin: 0;\">{verification_code}</h1>
            </div>
            <p>This code will expire in {self.settings.VERIFICATION_CODE_EXPIRE_MINUTES} minutes.</p>
            <p>If you did not request this change, you can safely ignore this email.</p>
            <br>
            <p>Best regards,<br>The Parotia Team</p>
        </body>
        </html>
        """

    def _create_password_reset_email_body(self, username: str, verification_code: str) -> str:
        return f"""
        <html>
        <body>
            <h2>Hello {username},</h2>
            <p>We received a request to reset your password. Use the verification code below to complete the process:</p>
            <div style=\"background-color: #f4f4f4; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;\">
                <h1 style=\"color: #333; font-size: 32px; letter-spacing: 8px; margin: 0;\">{verification_code}</h1>
            </div>
            <p>This code will expire in {self.settings.VERIFICATION_CODE_EXPIRE_MINUTES} minutes.</p>
            <p>If you did not request a password reset, please ignore this email.</p>
            <br>
            <p>Best regards,<br>The Parotia Team</p>
        </body>
        </html>
        """
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
            subject = "Email Verification Code - movAi"
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
            subject = "Email Change Verification - movAi"
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
            subject = "Password Reset Code - movAi"
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

    # =========================================================================
    # EMAIL HTML TEMPLATES
    # =========================================================================

    def _email_wrapper(self, content: str) -> str:
        """Shared modern email wrapper with movAi branding."""
        return f"""\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#0f0f1a;font-family:'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f0f1a;padding:40px 0;">
<tr><td align="center">
<table role="presentation" width="520" cellpadding="0" cellspacing="0" style="background:linear-gradient(145deg,#1a1a2e 0%,#16213e 100%);border-radius:16px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,0.5);">

<!-- Header -->
<tr><td style="padding:36px 40px 24px;text-align:center;border-bottom:1px solid rgba(255,255,255,0.06);">
<h1 style="margin:0;font-size:28px;font-weight:700;letter-spacing:1px;">
<span style="color:#a78bfa;">mov</span><span style="color:#ffffff;">Ai</span>
</h1>
</td></tr>

<!-- Body -->
<tr><td style="padding:32px 40px;">
{content}
</td></tr>

<!-- Footer -->
<tr><td style="padding:24px 40px 32px;text-align:center;border-top:1px solid rgba(255,255,255,0.06);">
<a href="https://movai.tr" style="color:#a78bfa;text-decoration:none;font-size:13px;font-weight:600;letter-spacing:0.5px;">movAi.tr</a>
<p style="margin:8px 0 0;color:#64748b;font-size:11px;">&copy; {datetime.now().year} movAi. All rights reserved.</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    def _code_block(self, code: str) -> str:
        """Glassmorphism-style verification code block."""
        return f"""\
<div style="background:rgba(167,139,250,0.08);border:1px solid rgba(167,139,250,0.25);border-radius:12px;padding:24px;text-align:center;margin:24px 0;">
<span style="font-size:36px;font-weight:700;letter-spacing:12px;color:#a78bfa;font-family:'Courier New',monospace;">{code}</span>
</div>
<p style="text-align:center;color:#94a3b8;font-size:12px;margin:4px 0 0;">This code expires in {self.settings.VERIFICATION_CODE_EXPIRE_MINUTES} minutes</p>"""

    def _create_verification_email_body(self, username: str, verification_code: str) -> str:
        content = f"""\
<h2 style="margin:0 0 8px;color:#ffffff;font-size:20px;font-weight:600;">Welcome, {username}!</h2>
<p style="color:#94a3b8;font-size:14px;line-height:1.6;margin:0 0 4px;">
Thank you for joining <strong style="color:#a78bfa;">movAi</strong>. Please verify your email address using the code below.
</p>
{self._code_block(verification_code)}
<p style="color:#64748b;font-size:12px;line-height:1.5;margin:16px 0 0;">
If you didn't create an account, you can safely ignore this email.
</p>"""
        return self._email_wrapper(content)

    def _create_email_change_email_body(self, username: str, verification_code: str, new_email: str) -> str:
        content = f"""\
<h2 style="margin:0 0 8px;color:#ffffff;font-size:20px;font-weight:600;">Email Change Request</h2>
<p style="color:#94a3b8;font-size:14px;line-height:1.6;margin:0 0 4px;">
Hi <strong style="color:#ffffff;">{username}</strong>, we received a request to change your email to
<strong style="color:#a78bfa;">{new_email}</strong>. Use the code below to confirm.
</p>
{self._code_block(verification_code)}
<p style="color:#64748b;font-size:12px;line-height:1.5;margin:16px 0 0;">
If you did not request this change, you can safely ignore this email.
</p>"""
        return self._email_wrapper(content)

    def _create_password_reset_email_body(self, username: str, verification_code: str) -> str:
        content = f"""\
<h2 style="margin:0 0 8px;color:#ffffff;font-size:20px;font-weight:600;">Password Reset</h2>
<p style="color:#94a3b8;font-size:14px;line-height:1.6;margin:0 0 4px;">
Hi <strong style="color:#ffffff;">{username}</strong>, we received a request to reset your password.
Use the code below to proceed.
</p>
{self._code_block(verification_code)}
<p style="color:#64748b;font-size:12px;line-height:1.5;margin:16px 0 0;">
If you did not request a password reset, please ignore this email.
</p>"""
        return self._email_wrapper(content)
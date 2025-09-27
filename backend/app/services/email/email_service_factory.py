from typing import Optional
from app.core.config import get_settings
from app.services.email.email_sender import EmailSender, SMTPEmailSender, ConsoleEmailSender, ResendEmailSender

class EmailServiceFactory:
    """Factory for creating email services"""
    
    @staticmethod
    def create_email_sender() -> EmailSender:
        """Create appropriate email sender based on configuration"""
        settings = get_settings()
        
        # Prefer Resend if configured
        if settings.RESEND_API_KEY and settings.RESEND_FROM_EMAIL:
            return ResendEmailSender(
                api_key=settings.RESEND_API_KEY,
                from_email=settings.RESEND_FROM_EMAIL,
            )
        # Else fallback to SMTP if credentials are available
        if (settings.SMTP_USERNAME and settings.SMTP_PASSWORD and settings.FROM_EMAIL):
            return SMTPEmailSender(
                smtp_server=settings.SMTP_SERVER,
                smtp_port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
                from_email=settings.FROM_EMAIL
            )
        else:
            # Fallback to console sender for development
            return ConsoleEmailSender() 
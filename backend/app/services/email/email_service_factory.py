from typing import Optional
from app.core.config import get_settings
from app.services.email.email_sender import EmailSender, SMTPEmailSender, ConsoleEmailSender

class EmailServiceFactory:
    """Factory for creating email services"""
    
    @staticmethod
    def create_email_sender() -> EmailSender:
        """Create appropriate email sender based on configuration"""
        settings = get_settings()
        
        # Check if SMTP credentials are available
        if (settings.SMTP_USERNAME and settings.SMTP_PASSWORD and 
            settings.FROM_EMAIL):
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
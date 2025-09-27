from abc import ABC, abstractmethod
from typing import Dict, Any
from app.core.config import get_settings

class EmailSender(ABC):
    """Abstract email sender interface"""
    
    @abstractmethod
    def send_email(self, to_email: str, subject: str, body: str, **kwargs) -> bool:
        """Send email"""
        pass

class SMTPEmailSender(EmailSender):
    """SMTP email sender implementation"""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str, from_email: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
    
    def send_email(self, to_email: str, subject: str, body: str, **kwargs) -> bool:
        """Send email via SMTP"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            return True
            
        except Exception as e:
            print(f"SMTP Error: {str(e)}")
            return False

class ConsoleEmailSender(EmailSender):
    """Console email sender for development"""
    
    def send_email(self, to_email: str, subject: str, body: str, **kwargs) -> bool:
        """Print email to console"""
        print("=" * 50)
        print("📧 EMAIL SENT")
        print("=" * 50)
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Body: {body}")
        if kwargs.get('verification_code'):
            print(f"Verification Code: {kwargs['verification_code']}")
        print("=" * 50)
        return True 


class ResendEmailSender(EmailSender):
    """Resend email sender implementation"""
    def __init__(self, api_key: str, from_email: str):
        import resend  # lazy import
        self.resend = resend
        self.resend.api_key = api_key
        self.from_email = from_email

    def send_email(self, to_email: str, subject: str, body: str, **kwargs) -> bool:
        try:
            params = {
                "from": self.from_email,
                "to": [to_email],
                "subject": subject,
                "html": body,
            }
            email = self.resend.Emails.send(params)  # type: ignore
            return True if email else False
        except Exception as e:
            print(f"Resend Error: {str(e)}")
            return False
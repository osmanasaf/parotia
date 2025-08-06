from fastapi import HTTPException, status

class BaseAppException(Exception):
    """Base exception for application"""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class UserNotFoundException(BaseAppException):
    """Raised when user is not found"""
    def __init__(self, message: str = "User not found"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)

class UserAlreadyExistsException(BaseAppException):
    """Raised when user already exists"""
    def __init__(self, message: str = "User already exists"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)
    
    def to_dict(self):
        """Return error response as dictionary with error code"""
        return {
            "error_code": "USER_ALREADY_EXISTS",
            "message": self.message,
            "status_code": self.status_code
        }

class InvalidCredentialsException(BaseAppException):
    """Raised when credentials are invalid"""
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)
    
    def to_dict(self):
        """Return error response as dictionary with error code"""
        return {
            "error_code": "INVALID_CREDENTIALS",
            "message": self.message,
            "status_code": self.status_code
        }

class EmailNotVerifiedException(BaseAppException):
    """Raised when email is not verified"""
    def __init__(self, message: str = "Email not verified"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)
    
    def to_dict(self):
        """Return error response as dictionary with error code"""
        return {
            "error_code": "EMAIL_NOT_VERIFIED",
            "message": self.message,
            "status_code": self.status_code
        }

class VerificationCodeExpiredException(BaseAppException):
    """Raised when verification code is expired"""
    def __init__(self, message: str = "Verification code expired"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)

class InvalidVerificationCodeException(BaseAppException):
    """Raised when verification code is invalid"""
    def __init__(self, message: str = "Invalid verification code"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)

class EmailServiceException(BaseAppException):
    """Raised when email service fails"""
    def __init__(self, message: str = "Email service error"):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR) 
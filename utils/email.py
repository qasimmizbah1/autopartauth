import os

async def send_verification_email(email: str, token: str, request):
    """
    Send verification email - in development, we'll print to console
    """
    verification_url = f"{request.base_url}v1/auth/verify-email?token={token}"
    
    if os.getenv("ENVIRONMENT") == "production":
        # Actual email sending logic for production
        # Use SendGrid, Mailgun, etc.
        pass
    else:
        # Development mode - print to console
        print(f"Verification email for: {email}")
        print(f"Verification URL: {verification_url}")
        print(f"Token: {token}")
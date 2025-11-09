import pyotp
import qrcode
from io import BytesIO
import base64
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken


def generate_mfa_secret():
    """Generate a new MFA secret key"""
    return pyotp.random_base32()


def generate_qr_code(user, secret):
    """Generate QR code for MFA setup"""
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name=settings.MFA_ISSUER_NAME
    )
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"


def verify_mfa_code(user, code):
    """Verify MFA code"""
    if not user.mfa_enabled or not user.mfa_secret:
        return False
    
    totp = pyotp.TOTP(user.mfa_secret)
    return totp.verify(code)


def get_tokens_for_user(user):
    """Generate JWT tokens for user"""
    refresh = RefreshToken.for_user(user)
    
    # Add custom claims
    refresh['email'] = user.email
    refresh['role'] = user.role
    
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }
from django.core.mail import send_mail
from django.conf import settings
import random
from datetime import datetime
from django.utils import timezone

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(email, otp):
    subject = 'Your OTP for Email Verification'
    message = f'Your OTP is: {otp}. This OTP will expire in 10 minutes.'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [email]
    
    send_mail(subject, message, from_email, recipient_list)

def send_password_reset_email(email, token):
    subject = 'Password Reset Request'
    message = f'Your password reset token is: {token}. This token will expire in 1 hour.'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [email]
    
    send_mail(subject, message, from_email, recipient_list) 
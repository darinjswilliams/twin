from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, EmailStr
import os
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict
import hashlib
import json

# Request model with CAPTCHA
class SecureResumeRequest(BaseModel):
    name: str
    email: EmailStr
    message: Optional[str] = ""
    captcha_token: str  # reCAPTCHA token
    # Honeypot fields
    website: Optional[str] = ""
    phone: Optional[str] = ""
    company: Optional[str] = ""
    js_enabled: Optional[str] = ""
    form_time: Optional[int] = 0

# Configuration
RECAPTCHA_SECRET = os.getenv("RECAPTCHA_SECRET_KEY")
RECAPTCHA_VERIFY_URL = os.getenv('RECAPTCHA_VERIFY_URL')
MAX_REQUESTS_PER_HOUR = os.getenv('MAX_REQUESTS_PER_HOUR')
MIN_CAPTCHA_SCORE = os.getenv('MIN_CAPTCHA_SCORE')
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL",  "")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "")
BREVO_API_URL = os.getenv("BREVO_API_URL","")
SENDER_NAME = os.getenv("SENDER_NAME", "")


# In-memory rate limiting (use DynamoDB in production)
from collections import defaultdict
rate_limit_tracker = defaultdict(list)


def verify_recaptcha(token: str, remote_ip: str) -> tuple[bool, float]:
    """Verify reCAPTCHA v3 token"""
    try:
        response = requests.post(
            RECAPTCHA_VERIFY_URL,
            data={
                'secret': RECAPTCHA_SECRET,
                'response': token,
                'remoteip': remote_ip
            },
            timeout=5
        )
        result = response.json()
        
        success = result.get('success', False)
        score = result.get('score', 0)
        
        return success, score
    except Exception as e:
        print(f"reCAPTCHA verification error: {e}")
        return False, 0.0


def check_rate_limit(email: str, ip: str) -> tuple[bool, str]:
    """Check if request exceeds rate limit"""
    # Create unique key from email and IP
    key = hashlib.sha256(f"{email}:{ip}".encode()).hexdigest()
    now = datetime.now()
    
    # Clean old requests (older than 1 hour)
    rate_limit_tracker[key] = [
        ts for ts in rate_limit_tracker[key] 
        if now - ts < timedelta(hours=1)
    ]
    
    # Check limit
    if len(rate_limit_tracker[key]) >= int(MAX_REQUESTS_PER_HOUR):
        next_allowed = rate_limit_tracker[key][0] + timedelta(hours=1)
        minutes_remaining = int((next_allowed - now).total_seconds() / 60)
        return False, f"Rate limit exceeded. Try again in {minutes_remaining} minutes."
    
    # Add current request
    rate_limit_tracker[key].append(now)
    return True, "OK"


def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    # Check for forwarded IP (from CloudFront/proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host

# HONEYPOT VALIDATION FUNCTION
def check_honeypot(request: SecureResumeRequest, client_ip: str, user_agent: str) -> tuple[bool, str]:
    """
    Check honeypot fields and behavioral patterns
    Returns: (is_valid, reason_if_invalid)
    """
    # 1. Check if honeypot fields are filled (bots often fill all fields)
    if request.website or request.phone or request.company:
        log_bot_attempt(client_ip, user_agent, "honeypot_filled", {
            "website": bool(request.website),
            "phone": bool(request.phone),
            "company": bool(request.company),
            "name": request.name,
            "email": request.email
        })
        return False, "Bot detected: honeypot field filled"
    
    # 2. Check if JavaScript is disabled (legitimate users should have JS)
    if request.js_enabled != "true":
        log_bot_attempt(client_ip, user_agent, "no_javascript", {
            "name": request.name,
            "email": request.email
        })
        return False, "Bot detected: JavaScript not enabled"
    
    # 3. Check form submission time (humans typically take 5+ seconds)
    MIN_FORM_TIME = 3  # seconds
    MAX_FORM_TIME = 3600  # 1 hour
    
    if request.form_time < MIN_FORM_TIME:
        log_bot_attempt(client_ip, user_agent, "too_fast", {
            "form_time": request.form_time,
            "name": request.name,
            "email": request.email
        })
        return False, f"Bot detected: form submitted too quickly ({request.form_time}s)"
    
    if request.form_time > MAX_FORM_TIME:
        log_bot_attempt(client_ip, user_agent, "stale_form", {
            "form_time": request.form_time,
            "name": request.name,
            "email": request.email
        })
        return False, "Form expired: please refresh and try again"
    
    return True, "OK"

 # BOT LOGGING FUNCTION
def log_bot_attempt(ip: str, user_agent: str, reason: str, details: dict):
    """Log suspected bot activity for analysis"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "ip": ip,
        "user_agent": user_agent,
        "reason": reason,
        "details": details,
        "type": "bot_attempt"
    }
    print(f"🤖 Bot attempt blocked: {json.dumps(log_entry)}")
    # In production, save to DynamoDB/CloudWatch for analysis   

def send_admin_notification(request_data: Dict):
    """Send notification to admin about resume request"""
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .alert {{ background: #4F46E5; color: white; padding: 20px; }}
            .details {{ background: #f9f9f9; padding: 20px; margin-top: 10px; }}
            .field {{ margin: 10px 0; }}
            .label {{ font-weight: bold; color: #4F46E5; }}
            .warning {{ color: #EF4444; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="alert">
            <h2>📄 Resume Request Received</h2>
        </div>
        <div class="details">
            <div class="field">
                <span class="label">Name:</span> {request_data['name']}
            </div>
            <div class="field">
                <span class="label">Email:</span> {request_data['email']}
            </div>
            <div class="field">
                <span class="label">Message:</span> {request_data.get('message', 'None')}
            </div>
            <div class="field">
                <span class="label">IP Address:</span> {request_data['ip']}
            </div>
            <div class="field">
                <span class="label">User Agent:</span> {request_data.get('user_agent', 'Unknown')}
            </div>
            <div class="field">
                <span class="label">CAPTCHA Score:</span> {request_data.get('captcha_score', 'N/A')}
                {' <span class="warning">⚠️ LOW SCORE</span>' if request_data.get('captcha_score', 1) < 0.5 else ''}
            </div>
            <div class="field">
                <span class="label">Timestamp:</span> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
            </div>
            <div class="field">
                <span class="label">Status:</span> Resume sent automatically ✅
            </div>
        </div>
    </body>
    </html>
    """
    try:
        # Send via Brevo
        print(f"Populating HTML to send not File to Admin: {SENDER_EMAIL}")
        payload = {
            "sender": {"name": str(request_data.get('name', 'Unknow')), 
            "email": str(request_data.get('email', 'no-reply@darindigialTwin.com'))},
            "to": [{"email": SENDER_EMAIL, "name": SENDER_NAME}],
            "subject": "Your Requested Resume - Darin Williams",
            "htmlContent": html_content
        }
        
        headers = {
            "api-key": BREVO_API_KEY,
            "Content-Type": "application/json"
        }
       
        print(f"Sending File to Admin: {SENDER_EMAIL}")
        
        response = requests.post(BREVO_API_URL, json=payload, headers=headers)
        return response.status_code == 201
    except Exception as e:
        print(f"Error sending resume: {e}")
        return False



def send_resume_to_user(name: str, email: str, pre_assigned_url: str) -> bool:
    """Send resume PDF to the requester"""
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #4F46E5; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .button {{ 
                background: #4F46E5; 
                color: white; 
                padding: 15px 30px; 
                text-decoration: none; 
                border-radius: 5px; 
                display: inline-block;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Your Resume Request</h2>
            </div>
            <div class="content">
                <p>Hi {name},</p>
                <p>Thank you for your interest! Please use the button below to download my resume. The link will remain active for one hour.</p>
                <a href="{pre_assigned_url}" class="button"><strong>Download Resume (PDF)</strong></a>
                <p>If you have any questions, feel free to reach out directly.</p>
                <p>Best regards,<br>Darin Williams</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        # Send via Brevo
        payload = {
            "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
            "to": [{"email": email, "name": name}],
            "subject": "Your Requested Resume - Darin Williams",
            "htmlContent": html_content
        }
        
        headers = {
            "api-key": BREVO_API_KEY,
            "Content-Type": "application/json"
        }
        
        response = requests.post(BREVO_API_URL, json=payload, headers=headers)
        return response.status_code == 201
    except Exception as e:
        print(f"Error sending resume: {e}")
        return False


def log_request(request_data: Dict):
    """Log request for analytics (save to S3/DynamoDB in production)"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "name": request_data["name"],
        "email": request_data["email"],
        "ip": request_data.get("ip"),
        "captcha_score": request_data.get("captcha_score"),
        "status": request_data.get("status"),
        "user_agent": request_data.get("user_agent")
    }
    
    print(f"Resume request log: {json.dumps(log_entry)}")
    
    # In production, save to S3:
    # s3_client.put_object(
    #     Bucket=LOGS_BUCKET,
    #     Key=f"resume-requests/{datetime.now().date()}/{uuid.uuid4()}.json",
    #     Body=json.dumps(log_entry)
    # )



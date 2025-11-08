from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import os
from dotenv import load_dotenv
from typing import Optional, Dict
import requests
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib

load_dotenv()

app = FastAPI()

# CORS - allow all localhost ports
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "null"  # For file:// protocol when opening HTML directly
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for local testing
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Configuration
RECAPTCHA_SECRET = os.getenv("RECAPTCHA_SECRET_KEY", "6LecxP4rAAAAAP82Po4nLAh9p0qQ5C-vLXU0UgMJ")
RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"
MAX_REQUESTS_PER_HOUR = 2
MIN_CAPTCHA_SCORE = 0.5

# Rate limiting tracker
rate_limit_tracker = defaultdict(list)


class SecureResumeRequest(BaseModel):
    name: str
    email: EmailStr
    message: Optional[str] = ""
    captcha_token: str


def verify_recaptcha(token: str, remote_ip: str) -> tuple[bool, float]:
    """Verify reCAPTCHA v3 token"""
    if not RECAPTCHA_SECRET:
        print("⚠️  RECAPTCHA_SECRET not set - skipping verification for testing")
        return True, 0.9  # Mock success for testing
    
    try:
        print(f"Verifying reCAPTCHA token from IP: {remote_ip}")
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
        
        print(f"reCAPTCHA response: {result}")
        
        success = result.get('success', False)
        score = result.get('score', 0)
        action = result.get('action', '')
        
        print(f"✓ Success: {success}, Score: {score}, Action: {action}")
        
        return success, score
    except Exception as e:
        print(f"❌ reCAPTCHA verification error: {e}")
        return False, 0.0


def check_rate_limit(email: str, ip: str) -> tuple[bool, str]:
    """Check if request exceeds rate limit"""
    key = hashlib.sha256(f"{email}:{ip}".encode()).hexdigest()
    now = datetime.now()
    
    # Clean old requests
    rate_limit_tracker[key] = [
        ts for ts in rate_limit_tracker[key] 
        if now - ts < timedelta(hours=1)
    ]
    
    # Check limit
    request_count = len(rate_limit_tracker[key])
    print(f"Rate limit check: {request_count}/{MAX_REQUESTS_PER_HOUR} requests in last hour")
    
    if request_count >= MAX_REQUESTS_PER_HOUR:
        next_allowed = rate_limit_tracker[key][0] + timedelta(hours=1)
        minutes_remaining = int((next_allowed - now).total_seconds() / 60)
        return False, f"Rate limit exceeded. Try again in {minutes_remaining} minutes."
    
    # Add current request
    rate_limit_tracker[key].append(now)
    return True, "OK"


def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


def send_mock_resume_email(name: str, email: str) -> bool:
    """Mock function that simulates sending resume"""
    print("=" * 50)
    print("📧 MOCK EMAIL - Resume Sent")
    print("=" * 50)
    print(f"To: {email}")
    print(f"Subject: Your Requested Resume - Darin Williams")
    print(f"Body:")
    print(f"""
    Hi {name},
    
    Thank you for your interest! Here's the link to download my resume:
    
    [MOCK DOWNLOAD LINK: https://example.com/resume.pdf]
    
    Best regards,
    Darin Williams
    """)
    print("=" * 50)
    return True


def send_mock_admin_notification(request_data: Dict):
    """Mock function that simulates admin notification"""
    print("=" * 50)
    print("🔔 MOCK ADMIN NOTIFICATION")
    print("=" * 50)
    print(f"Resume requested by: {request_data['name']}")
    print(f"Email: {request_data['email']}")
    print(f"Message: {request_data.get('message', 'None')}")
    print(f"IP: {request_data['ip']}")
    print(f"CAPTCHA Score: {request_data.get('captcha_score', 'N/A')}")
    print(f"User Agent: {request_data.get('user_agent', 'Unknown')}")
    print(f"Timestamp: {datetime.now()}")
    print("=" * 50)


@app.get("/")
async def root():
    return {
        "message": "Local Resume Testing API",
        "recaptcha_configured": bool(RECAPTCHA_SECRET),
        "endpoints": [
            "POST /send-resume-request-secure",
            "GET /test-recaptcha"
        ]
    }


@app.get("/test-recaptcha")
async def test_recaptcha():
    """Test endpoint to verify reCAPTCHA configuration"""
    return {
        "recaptcha_secret_set": bool(RECAPTCHA_SECRET),
        "recaptcha_secret_preview": RECAPTCHA_SECRET[:10] + "..." if RECAPTCHA_SECRET else "NOT SET",
        "verify_url": RECAPTCHA_VERIFY_URL,
        "min_score": MIN_CAPTCHA_SCORE,
        "rate_limit": f"{MAX_REQUESTS_PER_HOUR} requests per hour"
    }


@app.post("/send-resume-request-secure")
async def send_resume_request_secure(request: SecureResumeRequest, req: Request):
    """
    Secure endpoint with CAPTCHA and rate limiting (LOCAL TESTING VERSION)
    """
    try:
        print("\n" + "=" * 50)
        print("📝 NEW RESUME REQUEST")
        print("=" * 50)
        
        # Get client info
        client_ip = get_client_ip(req)
        user_agent = req.headers.get("User-Agent", "Unknown")
        
        print(f"Name: {request.name}")
        print(f"Email: {request.email}")
        print(f"IP: {client_ip}")
        print(f"User Agent: {user_agent[:50]}...")
        
        # 1. Verify CAPTCHA
        print("\n🔐 Verifying reCAPTCHA...")
        captcha_valid, captcha_score = verify_recaptcha(
            request.captcha_token, 
            client_ip
        )
        
        if not captcha_valid:
            print(f"❌ CAPTCHA verification failed!")
            raise HTTPException(
                status_code=403,
                detail="CAPTCHA verification failed. Please try again."
            )
        
        if captcha_score < MIN_CAPTCHA_SCORE:
            print(f"❌ CAPTCHA score too low: {captcha_score} < {MIN_CAPTCHA_SCORE}")
            raise HTTPException(
                status_code=403,
                detail=f"Security check failed (score: {captcha_score}). Please try again."
            )
        
        print(f"✅ CAPTCHA verified! Score: {captcha_score}")
        
        # 2. Check rate limit
        print("\n⏱️  Checking rate limit...")
        rate_limit_ok, rate_limit_msg = check_rate_limit(request.email, client_ip)
        
        if not rate_limit_ok:
            print(f"❌ Rate limit exceeded!")
            raise HTTPException(status_code=429, detail=rate_limit_msg)
        
        print(f"✅ Rate limit OK")
        
        # 3. Send mock resume to user
        print("\n📤 Sending resume to user...")
        resume_sent = send_mock_resume_email(request.name, request.email)
        
        if not resume_sent:
            raise HTTPException(
                status_code=500,
                detail="Failed to send resume. Please try again."
            )
        
        print("✅ Resume sent to user")
        
        # 4. Send mock admin notification
        print("\n📬 Sending admin notification...")
        send_mock_admin_notification({
            "name": request.name,
            "email": request.email,
            "message": request.message,
            "ip": client_ip,
            "user_agent": user_agent,
            "captcha_score": captcha_score
        })
        
        print("\n" + "=" * 50)
        print("✅ REQUEST COMPLETED SUCCESSFULLY")
        print("=" * 50 + "\n")
        
        return {
            "success": True,
            "message": "Resume sent! Check your email.",
            "debug_info": {
                "captcha_score": captcha_score,
                "rate_limit_remaining": MAX_REQUESTS_PER_HOUR - len(rate_limit_tracker[hashlib.sha256(f"{request.email}:{client_ip}".encode()).hexdigest()])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 50)
    print("🚀 Starting Local Testing Server")
    print("=" * 50)
    print("Make sure to set RECAPTCHA_SECRET_KEY in .env")
    print("Server running at: http://localhost:8000")
    print("=" * 50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
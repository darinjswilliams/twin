
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import os
from dotenv import load_dotenv
from typing import Optional, List, Dict
import json
import uuid
from datetime import datetime
from pathlib import Path
from email_services import (
    SecureResumeRequest,
    verify_recaptcha,
    check_rate_limit,
    get_client_ip,
    send_admin_notification,
    send_resume_to_user,
    log_request,
    check_honeypot
)

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from context import prompt

# Load environment variables
load_dotenv(override=True)

app = FastAPI()


# Configure CORS
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
MIN_CAPTCHA_SCORE = os.getenv("MIN_CAPTCHA_SCORE")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize Bedrock client
bedrock_client = boto3.client(
    service_name="bedrock-runtime", 
    region_name=os.getenv("DEFAULT_AWS_REGION", "us-east-2")
)

# Bedrock model selection
# Available models:
# - amazon.nova-micro-v1:0  (fastest, cheapest)
# - amazon.nova-lite-v1:0   (balanced - default)
# - amazon.nova-pro-v1:0    (most capable, higher cost)
# Remember the Heads up: you might need to add us. or eu. prefix to the below model id
BEDROCK_MODEL_ID=os.getenv("BEDROCK_MODEL_ID", "arn:aws:bedrock:us-east-2:472730590621:inference-profile/global.amazon.nova-2-lite-v1:0")


# Memory storage configuration
USE_S3 = os.getenv("USE_S3", "false").lower() == "true"
S3_BUCKET = os.getenv("S3_BUCKET", "")
MEMORY_DIR = os.getenv("MEMORY_DIR", "../memory")
RESUME_NAME=os.getenv("RESUME_NAME")

# Initialize S3 client if needed
if USE_S3:
    s3_client = boto3.client("s3", region_name='us-east-2',
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}))

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    

class Message(BaseModel):
    role: str
    content: str
    timestamp: str


class ResumeRequest(BaseModel):
    name: str
    email: EmailStr
    message: Optional[str] = ""


class EmailResponse(BaseModel):
    success: bool
    message: str
    message_id: Optional[str] = None

# Memory management functions
def get_memory_path(session_id: str) -> str:
    return f"{session_id}.json"


# Memory functions
def load_conversation(session_id: str) -> List[Dict]:
    """Load conversation history from storage"""
    if USE_S3:
        try:
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=get_memory_path(session_id))
            return json.loads(response["Body"].read().decode("utf-8"))
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return []
            raise
    else:
        # Local file storage
        file_path = os.path.join(MEMORY_DIR, get_memory_path(session_id))
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
        return []


def save_conversation(session_id: str, messages: List[Dict]):
    """Save conversation history to storage"""
    if USE_S3:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=get_memory_path(session_id),
            Body=json.dumps(messages, indent=2),
            ContentType="application/json",
        )
    else:
        # Local file storage
        os.makedirs(MEMORY_DIR, exist_ok=True)
        file_path = os.path.join(MEMORY_DIR, get_memory_path(session_id))
        with open(file_path, "w") as f:
            json.dump(messages, f, indent=2)

def call_bedrock(conversation: List[Dict], user_message: str) -> str:
    """Call AWS Bedrock with conversation history"""
    
    # Build messages in Bedrock format
    messages = []
    
    # Add system prompt as first user message (Bedrock convention)
    messages.append({
        "role": "user", 
        "content": [{"text": f"System: {prompt()}"}]
    })
    
    # Add conversation history (limit to last 10 exchanges to manage context)
    for msg in conversation[-10:]:  # Last 10 back-and-forth exchanges
        messages.append({
            "role": msg["role"],
            "content": [{"text": msg["content"]}]
        })
    
    # Add current user message
    messages.append({
        "role": "user",
        "content": [{"text": user_message}]
    })
    
    try:
        # Call Bedrock using the converse API
        response = bedrock_client.converse(
            modelId=BEDROCK_MODEL_ID,
            messages=messages,
            inferenceConfig={
                "maxTokens": 256,
                "temperature": 0.7,
                "topP": 0.9
            }
        )
        
        # Extract the response text
        return response["output"]["message"]["content"][0]["text"]
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ValidationException':
            # Handle message format issues
            print(f"Bedrock validation error: {e}")
            raise HTTPException(status_code=400, detail="Invalid message format for Bedrock")
        elif error_code == 'AccessDeniedException':
            print(f"Bedrock access denied: {e}")
            raise HTTPException(status_code=403, detail="Access denied to Bedrock model")
        elif error_code == 'ThrottlingExcepton':
            print(f'Bedrock throttling exception: {e}')
            raise HTTPException(status_code=429, detail="Modal quota reached for today. Please retry after the daily reset")
        else:
            print(f"Bedrock error: {e}")
            raise HTTPException(status_code=500, detail=f"Bedrock error: {str(e)}")
    




def generate_resume_presigned_url(
    bucket_name: str = S3_BUCKET,
    object_key: str = RESUME_NAME,
    expires_in: int = 3600
) -> str:
    """
    Generate a presigned URL to download the resume from S3.

    Args:
        bucket_name (str): Name of the S3 bucket.
        object_key (str): Key (path/filename) of the object in S3.
        expires_in (int): Expiration time in seconds (default: 3600 = 1 hour).

    Returns:
        str: A presigned URL string if successful, else None.
    """
    if not bucket_name:
        raise ValueError("S3_BUCKET not configured in environment variables")
    
    if not object_key:
        raise ValueError("RESUME_NAME not configured in environment variables")



    try:

        print(f"Generating presigned URL for s3://{bucket_name}/{object_key}")
        print(f"Expiration: {expires_in} seconds ({expires_in/60:.1f} minutes)")


        url = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": bucket_name,
                "Key": object_key
            },
            ExpiresIn=expires_in,
            HttpMethod="GET"
        )

        print(f"✅ Presigned URL generated successfully")
        print(f"URL (first 80 chars): {url[:80]}...")

        return url
    except ClientError as e:
        print(f"Error generating presigned URL: {e}")
        return None

# Backend - verify token

@app.get("/")
async def root():
    return {
        "message": "AI Digital Twin API",
        "memory_enabled": True,
        "storage": "S3" if USE_S3 else "local",
        "ai_model": BEDROCK_MODEL_ID
    }


@app.get("/health")
async def health_check():
      return {
        "status": "healthy", 
        "use_s3": USE_S3,
        "bedrock_model": BEDROCK_MODEL_ID
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())

        # Load conversation history
        conversation = load_conversation(session_id)

       # Call Bedrock for response
        assistant_response = call_bedrock(conversation, request.message)

      # Update conversation history
        conversation.append(
            {"role": "user", "content": request.message, "timestamp": datetime.now().isoformat()}
        )
        conversation.append(
            {
                "role": "assistant",
                "content": assistant_response,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Save conversation
        save_conversation(session_id, conversation)

        return ChatResponse(response=assistant_response, session_id=session_id)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/conversation/{session_id}")
async def get_conversation(session_id: str):
    """Retrieve conversation history"""
    try:
        conversation = load_conversation(session_id)
        return {"session_id": session_id, "messages": conversation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/send-resume-request-secure")
async def send_resume_request_secure(request: SecureResumeRequest, req: Request):
    """
    Secure endpoint with CAPTCHA, rate limiting, and notifications
    """
    try:
        # Get client info
        client_ip = get_client_ip(req)
        user_agent = req.headers.get("User-Agent", "Unknown")
        
       #1. Check honeypot FIRST (fastest check, blocks obvious bots)
        honeypot_valid, honeypot_msg = check_honeypot(request, client_ip, user_agent)
        if not honeypot_valid:
            print(f"❌ Honeypot failed: {honeypot_msg}")
            log_request({
                "name": request.name,
                "email": request.email,
                "ip": client_ip,
                "status": "blocked_honeypot",
                "reason": honeypot_msg,
                "user_agent": user_agent,
                "form_time": request.form_time
            })
            # Return generic error to avoid revealing bot detection method
            raise HTTPException(
                status_code=403,
                detail="Request validation failed. Please try again."
            )
        else:
             print(f"✅ Honeypot passed!")
        
        # 2. Verify CAPTCHA
        captcha_valid, captcha_score = verify_recaptcha(
            request.captcha_token, 
            client_ip
        )
        
        if not captcha_valid or captcha_score < float(MIN_CAPTCHA_SCORE):
            log_request({
                "name": request.name,
                "email": request.email,
                "ip": client_ip,
                "captcha_score": captcha_score,
                "status": "blocked_captcha",
                "user_agent": user_agent
            })
            raise HTTPException(
                status_code=403,
                detail="CAPTCHA verification failed. Please try again."
            )
        
        
        if not captcha_valid or captcha_score < float(MIN_CAPTCHA_SCORE):
            log_request({
                "name": request.name,
                "email": request.email,
                "ip": client_ip,
                "captcha_score": captcha_score,
                "status": "blocked_captcha",
                "user_agent": user_agent
            })
            raise HTTPException(
                status_code=403,
                detail="CAPTCHA verification failed. Please try again."
            )
        
        # 2. Check rate limit
        rate_limit_ok, rate_limit_msg = check_rate_limit(request.email, client_ip)
        if not rate_limit_ok:
            log_request({
                "name": request.name,
                "email": request.email,
                "ip": client_ip,
                "captcha_score": captcha_score,
                "status": "blocked_rate_limit",
                "user_agent": user_agent
            })
            raise HTTPException(status_code=429, detail=rate_limit_msg)

        # generate preassigned url
        pre_assigned_url = generate_resume_presigned_url()
        
        # 3. Send resume to user
        resume_sent = send_resume_to_user(name=request.name, email=request.email, pre_assigned_url=pre_assigned_url)
        
        if not resume_sent:
            raise HTTPException(
                status_code=500,
                detail="Failed to send resume. Please try again."
            )
        
        # 4. Send notification to admin (you)
        send_admin_notification({
            "name": request.name,
            "email": request.email,
            "message": request.message,
            "ip": client_ip,
            "user_agent": user_agent,
            "captcha_score": captcha_score,
            "form_time": request.form_time,
            "honeypot_passed": True
        })
        
        # 5. Log the successful request
        log_request({
            "name": request.name,
            "email": request.email,
            "ip": client_ip,
            "captcha_score": captcha_score,
            "form_time": request.form_time,
            "status": "sent",
            "user_agent": user_agent
        })
        
        return {
            "success": True,
            "message": "Resume sent! Check your email."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in secure resume endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
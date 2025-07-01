from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from app.auth.models.auth import SignUpRequest, ConfirmSignUpRequest, SignInRequest, RefreshTokenRequest
from app.auth.services.cognito_service import (
    sign_up_user, confirm_user_signup, sign_in_user, 
    refresh_user_token, get_user_info, verify_access_token
)
from botocore.exceptions import ClientError

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/signup")
def signup(req: SignUpRequest):
    try:
        result = sign_up_user(req.email, req.password)  
        return {"email": req.email, **result}
    except ClientError as e:
        raise HTTPException(status_code=400, detail=e.response["Error"]["Message"])
    
@router.post("/confirm")
def confirm_signup(req: ConfirmSignUpRequest):
    try:
        return confirm_user_signup(req.email, req.code)
    except ClientError as e:
        raise HTTPException(status_code=400, detail=e.response["Error"]["Message"])
    
@router.post("/login")
def login(req: SignInRequest):
    try:
        return sign_in_user(req.email, req.password)
    except ClientError as e:
        raise HTTPException(status_code=400, detail=e.response["Error"]["Message"])

@router.post("/refresh")
def refresh_token(req: RefreshTokenRequest):
    try:
        return refresh_user_token(req.refresh_token, req.email)
    except ClientError as e:
        raise HTTPException(status_code=401, detail=e.response["Error"]["Message"])

@router.get("/me")
def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")
    access_token = authorization.split(" ")[1]
    try:
        return get_user_info(access_token)
    except ClientError as e:
        raise HTTPException(status_code=401, detail=e.response["Error"]["Message"])

@router.get("/verify")
def verify_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")
    access_token = authorization.split(" ")[1]
    result = verify_access_token(access_token)
    if not result["valid"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result 
# backend/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin             # the real SDK
from firebase_admin import auth as fb_auth
import backend.app.firebase_client as firebase_client            # your init code (formerly firebase_admin.py)

app = FastAPI()
security = HTTPBearer()  # looks for “Authorization: Bearer <token>”

async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security)
):
    token = creds.credentials
    try:
        decoded = fb_auth.verify_id_token(token)
        return decoded
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/protected")
async def protected_route(user=Depends(get_current_user)):
    # decoded token contains “uid”, “email”, etc.
    return {
        "message": f"Hello, {user.get('email')} (uid: {user.get('uid')})"
    }
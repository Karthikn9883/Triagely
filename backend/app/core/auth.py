from dotenv import load_dotenv           #  add

import os, time, requests
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv()  

REGION      = os.getenv("AWS_REGION")
POOL_ID     = os.getenv("COG_USER_POOL_ID")
CLIENT_ID   = os.getenv("COG_APP_CLIENT_ID")

_ISSUER = f"https://cognito-idp.{REGION}.amazonaws.com/{POOL_ID}"
_JWKS_URL = f"{_ISSUER}/.well-known/jwks.json"
_cache, _ts, _ttl = None, 0, 60 * 60 * 6  # 6 h

def _jwks():
    global _cache, _ts
    if not _cache or time.time() - _ts > _ttl:
        _cache = requests.get(_JWKS_URL, timeout=5).json()["keys"]
        _ts = time.time()
    return _cache

def verify(token: str) -> dict:
    try:
        kid = jwt.get_unverified_header(token)["kid"]
        key = next(k for k in _jwks() if k["kid"] == kid)

        claims: dict = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=CLIENT_ID,
            issuer=_ISSUER,
        )

        # ▸▸▸ Normalise the user’s “username” so the frontend
        # can rely on claims['username'] always existing.
        username = (
            claims.get("custom:username")               # if you stored it as a custom attribute
            or claims.get("preferred_username")
            or claims.get("cognito:username")
            or claims.get("username")
            or claims.get("name")
            or claims.get("email", "").split("@")[0]    # fallback: left-hand side of the email
        )
        claims["username"] = username

        return claims

    except (StopIteration, JWTError):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token",
        )

security = HTTPBearer()

async def current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    return verify(creds.credentials)

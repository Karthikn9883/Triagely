# app/core/auth.py

"""
Authentication utilities for Triagely backend.

Handles JWT verification against AWS Cognito User Pool,
extracts/refreshes public keys, normalises user claims,
and provides FastAPI dependency for secured endpoints.
"""
from dotenv import load_dotenv
import os
import time
import requests
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Load environment variables from .env (e.g., AWS_REGION, COG_USER_POOL_ID)
load_dotenv()

# AWS Cognito config from env
REGION      = os.getenv("AWS_REGION")
POOL_ID     = os.getenv("COG_USER_POOL_ID")
CLIENT_ID   = os.getenv("COG_APP_CLIENT_ID")

# Construct JWT issuer URL and JWKS endpoint
_ISSUER    = f"https://cognito-idp.{REGION}.amazonaws.com/{POOL_ID}"
_JWKS_URL  = f"{_ISSUER}/.well-known/jwks.json"

# In-memory cache for JWKs to avoid frequent HTTP calls
_cache, _ts, _ttl = None, 0, 60 * 60 * 6  # cache timeout = 6 hours


def _jwks() -> list[dict]:
    """
    Fetch and cache JWKS keys from AWS Cognito.
    Refreshes the cache if older than TTL.

    Returns:
        A list of JSON Web Key dicts for token signature verification.
    """
    global _cache, _ts
    if not _cache or (time.time() - _ts) > _ttl:
        # Retrieve JWKS JSON and update timestamp
        resp = requests.get(_JWKS_URL, timeout=5)
        resp.raise_for_status()
        _cache = resp.json().get("keys", [])
        _ts = time.time()
    return _cache


def verify(token: str) -> dict:
    """
    Verify a JWT access token issued by AWS Cognito.

    Steps:
      1. Decode token header to get 'kid'.
      2. Find matching JWK by 'kid'.
      3. Decode and validate signature, issuer, and audience.
      4. Normalize a 'username' claim for frontend use.

    Args:
      token: Raw JWT string from HTTP Authorization header.

    Returns:
      Decoded claims dict, with an added 'username' key.

    Raises:
      HTTPException(401) if token is invalid or expired.
    """
    try:
        # 1️⃣ Extract 'kid' from unverified header
        kid = jwt.get_unverified_header(token)["kid"]
        # 2️⃣ Locate corresponding key in JWKS
        key = next(k for k in _jwks() if k.get("kid") == kid)

        # 3️⃣ Decode and verify token signature and standard claims
        claims: dict = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=CLIENT_ID,
            issuer=_ISSUER,
        )

        # Normalize 'username' so frontend can rely on claim
        username = (
            claims.get("custom:username")                # custom attribute
            or claims.get("preferred_username")           # preferred_username
            or claims.get("cognito:username")            # Cognito-generated username
            or claims.get("username")
            or claims.get("name")
            or claims.get("email", "").split("@")[0]  # fallback to email local-part
        )
        claims["username"] = username
        return claims

    except StopIteration:
        # No matching JWK found
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid token: unknown 'kid'",
        )
    except JWTError:
        # Token decode/validation error
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token",
        )

# FastAPI security scheme (looks for Bearer auth header)
security = HTTPBearer()

async def current_user(
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    FastAPI dependency that extracts and verifies the current user.

    Usage in routes:
      @router.get(...)
      def protected_route(user = Depends(current_user)):
          # 'user' is the decoded JWT claims dict
    """
    return verify(creds.credentials)

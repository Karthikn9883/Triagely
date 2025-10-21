# app/core/auth.py

"""
Authentication utilities for Triagely backend.

Handles JWT generation and verification for local user authentication,
provides FastAPI dependency for secured endpoints.
"""
from dotenv import load_dotenv
import os
import uuid
import bcrypt
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.db import get_user_by_email, get_user_by_id, create_user

# Load environment variables from .env
load_dotenv()

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# FastAPI security scheme (looks for Bearer auth header)
security = HTTPBearer()


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.

    Args:
      password: Plain text password.

    Returns:
      Hashed password string.
    """
    # Convert password to bytes and hash it
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string for database storage
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.

    Args:
      plain_password: Plain text password to verify.
      hashed_password: Hashed password to compare against.

    Returns:
      True if password matches, False otherwise.
    """
    # Convert both to bytes for bcrypt
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(user_id: str, email: str, name: str = None) -> str:
    """
    Create a JWT access token for a user.

    Args:
      user_id: User's unique identifier.
      email: User's email address.
      name: User's full name (optional).

    Returns:
      JWT token string.
    """
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": user_id,
        "email": email,
        "name": name,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Verify a JWT access token.

    Args:
      token: JWT token string.

    Returns:
      Decoded claims dict with 'sub', 'email', 'name', etc.

    Raises:
      HTTPException(401) if token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        # Normalize username for consistency
        username = (
            payload.get("name") or
            payload.get("email", "").split("@")[0]
        )
        payload["username"] = username
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


async def current_user(
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    FastAPI dependency that extracts and verifies the current user.

    Usage in routes:
      @router.get(...)
      def protected_route(user = Depends(current_user)):
          # 'user' is the decoded JWT claims dict with 'sub', 'email', etc.
    """
    return verify_token(creds.credentials)


def register_user(email: str, password: str, name: str = None) -> dict:
    """
    Register a new user account.

    Args:
      email: User's email address (must be unique).
      password: Plain text password.
      name: User's full name (optional).

    Returns:
      Dict with user info and access token.

    Raises:
      HTTPException(400) if email already exists.
    """
    # Check if user already exists
    existing_user = get_user_by_email(email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    create_user(user_id, email, password_hash, name)

    # Generate token
    token = create_access_token(user_id, email, name)

    return {
        "user_id": user_id,
        "email": email,
        "name": name,
        "access_token": token,
        "token_type": "bearer"
    }


def login_user(email: str, password: str) -> dict:
    """
    Authenticate a user and return an access token.

    Args:
      email: User's email address.
      password: Plain text password.

    Returns:
      Dict with user info and access token.

    Raises:
      HTTPException(401) if credentials are invalid.
    """
    # Get user by email
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Generate token
    token = create_access_token(user["id"], user["email"], user.get("name"))

    return {
        "user_id": user["id"],
        "email": user["email"],
        "name": user.get("name"),
        "access_token": token,
        "token_type": "bearer"
    }

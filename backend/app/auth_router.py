# app/auth_router.py

"""
Authentication router for Triagely backend.
Handles user registration, login, and profile endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.core.auth import register_user, login_user, current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
async def register(req: RegisterRequest):
    """
    Register a new user account.

    Args:
      req: Registration request with email, password, and optional name.

    Returns:
      User info and access token.

    Raises:
      400: Email already registered.
    """
    return register_user(req.email, req.password, req.name)


@router.post("/login")
async def login(req: LoginRequest):
    """
    Login to an existing account.

    Args:
      req: Login request with email and password.

    Returns:
      User info and access token.

    Raises:
      401: Invalid credentials.
    """
    return login_user(req.email, req.password)


@router.get("/me")
async def get_current_user(user=Depends(current_user)):
    """
    Get the current authenticated user's profile.

    Args:
      user: Decoded JWT token (from current_user dependency).

    Returns:
      User profile info.
    """
    return {
        "user_id": user.get("sub"),
        "email": user.get("email"),
        "name": user.get("name"),
        "username": user.get("username")
    }

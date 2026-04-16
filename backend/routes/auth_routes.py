"""
Auth routes: login, logout, session management.
POST /login - authenticate with username + PIN
POST /logout - invalidate session
GET /me - get current user info
GET /users - list users (admin only)
POST /users - create user (admin only)
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])
service = AuthService()


class LoginIn(BaseModel):
    username: str
    pin: str


class UserCreateIn(BaseModel):
    username: str
    pin: str
    display_name: Optional[str] = None
    role: str = "worker"
    employee_id: Optional[int] = None


def get_current_user(request: Request) -> dict | None:
    """Extract and validate the session token from request headers."""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return None
    return service.validate_token(token)


def require_auth(request: Request) -> dict:
    """Require authentication. Returns user or raises 401."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_admin(request: Request) -> dict:
    """Require admin role. Returns user or raises 403."""
    user = require_auth(request)
    if user["role"] not in ("admin", "office"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/workers")
def list_workers():
    """List active worker accounts (for touch-screen login grid). No auth required."""
    try:
        users = service.list_users()
        # Only return workers with minimal info for the login grid
        workers = [
            {"id": u["id"], "username": u["username"], "display_name": u["display_name"],
             "role": u["role"], "employee_id": u.get("employee_id")}
            for u in users if u.get("is_active", 1) and u.get("role") == "worker"
        ]
        return workers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
def login(data: LoginIn):
    """Login with username and PIN."""
    try:
        result = service.login(data.username, data.pin)
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
def logout(request: Request):
    """Logout and invalidate session."""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        service.logout(token)
    return {"message": "Logged out"}


@router.get("/me")
def get_me(request: Request):
    """Get current authenticated user info."""
    user = require_auth(request)
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "role": user["role"],
        "employee_id": user["employee_id"],
    }


@router.get("/users")
def list_users(request: Request):
    """List all users (admin/office only)."""
    require_admin(request)
    return service.list_users()


@router.post("/users")
def create_user(data: UserCreateIn, request: Request):
    """Create a new user (admin only)."""
    user = require_auth(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create users")
    try:
        user_id = service.create_user(data.dict())
        return {"id": user_id, "message": "User created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

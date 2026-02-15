from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime

from models import UserCreate, UserInDB, UserResponse
from services import hash_password, verify_password, generate_token, FileStorage

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)


def get_storage() -> FileStorage:
    """Dependency to get storage instance."""
    import os
    data_dir = os.getenv("SPLITWISE_DATA_DIR", "/app/data")
    return FileStorage(data_dir)


async def get_current_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    storage: FileStorage = Depends(get_storage),
) -> UserInDB:
    """Get current user from Bearer token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    user_data = storage.get_user_by_token(credentials.credentials)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    return UserInDB(**user_data)


async def get_current_user_from_session(
    session_token: Optional[str] = Cookie(None),
    storage: FileStorage = Depends(get_storage),
) -> Optional[UserInDB]:
    """Get current user from session cookie."""
    if not session_token:
        return None

    user_data = storage.get_user_by_token(session_token)
    if not user_data:
        return None

    return UserInDB(**user_data)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, storage: FileStorage = Depends(get_storage)):
    """Register a new user."""
    # Check if username already exists
    existing_user = storage.get_user_by_username(user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # Create user
    user_in_db = UserInDB(
        username=user.username,
        display_name=user.display_name,
        password_hash=hash_password(user.password),
    )

    user_dict = user_in_db.model_dump()
    storage.create_user(user_dict)

    return UserResponse(**user_dict, api_token=user_in_db.api_token)


@router.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
    response: Response = None,
    storage: FileStorage = Depends(get_storage),
):
    """Login with username and password."""
    user_data = storage.get_user_by_username(username)

    if not user_data or not verify_password(password, user_data["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    user = UserInDB(**user_data)

    # Set session cookie
    response.set_cookie(
        key="session_token",
        value=user.api_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30 * 24 * 60 * 60,  # 30 days
    )

    return {
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
        },
        "api_token": user.api_token,
    }


@router.post("/logout")
async def logout(response: Response):
    """Logout and clear session."""
    response.delete_cookie("session_token")
    return {"message": "Logout successful"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: UserInDB = Depends(get_current_user_from_token),
):
    """Get current authenticated user."""
    return UserResponse(**current_user.model_dump())

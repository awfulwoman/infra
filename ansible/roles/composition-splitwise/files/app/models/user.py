from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class User(UserBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class UserInDB(User):
    password_hash: str
    api_token: str = Field(default_factory=lambda: str(uuid.uuid4().hex))


class UserResponse(User):
    api_token: Optional[str] = None

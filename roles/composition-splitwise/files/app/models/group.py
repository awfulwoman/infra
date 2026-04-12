from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel, Field
import uuid


class GroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    members: List[str] = Field(..., min_items=2)


class GroupCreate(GroupBase):
    pass


class Group(GroupBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class GroupResponse(Group):
    balances: Dict[str, float] = Field(default_factory=dict)

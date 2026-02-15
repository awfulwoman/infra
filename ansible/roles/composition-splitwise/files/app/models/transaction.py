from datetime import datetime
from typing import Dict, Literal
from pydantic import BaseModel, Field
import uuid


class TransactionBase(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = Field(default="GBP", max_length=3)
    payer_id: str
    description: str = Field(..., min_length=1, max_length=500)
    split_type: Literal["equal"] = "equal"


class TransactionCreate(TransactionBase):
    group_id: str


class TransactionUpdate(BaseModel):
    amount: float | None = Field(None, gt=0)
    description: str | None = Field(None, min_length=1, max_length=500)
    payer_id: str | None = None


class Transaction(TransactionBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    group_id: str
    split_details: Dict[str, float] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str

    class Config:
        from_attributes = True

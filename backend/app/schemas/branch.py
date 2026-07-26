import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class BranchBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=20)
    monthly_sales_target: Optional[float] = Field(None, description="Target monthly sales in INR")

class BranchCreate(BranchBase):
    pass

class BranchResponse(BranchBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_serializer

class DailyReportCreate(BaseModel):
    date: date
    sales_amount: float = Field(..., ge=0, description="Daily sales amount in INR")
    attendance_count: int = Field(..., ge=0, description="Total present count")
    target_achievement: float = Field(..., ge=0, description="Achievement level in percentage")
    inventory_status: Optional[str] = Field(None, max_length=500)
    remarks: Optional[str] = Field(None, max_length=1000)
    issues: Optional[str] = Field(None, max_length=1000)
    original_file_url: Optional[str] = Field(None, max_length=500)

class DailyReportResponse(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID
    manager_id: uuid.UUID
    date: date
    sales_amount: float
    attendance_count: int
    target_achievement: float
    inventory_status: Optional[str]
    remarks: Optional[str]
    issues: Optional[str]
    # New production template fields
    gold: Optional[float] = 0.0
    diamond: Optional[float] = 0.0
    platinum: Optional[float] = 0.0
    silver: Optional[float] = 0.0
    silver_mrp: Optional[float] = 0.0
    total_revenue: Optional[float] = 0.0
    digigold: Optional[int] = 0
    digisilver: Optional[int] = 0
    # Additional fields from dc721e0 branch
    gold_weight: Optional[str] = None
    diamond_weight: Optional[str] = None
    platinum_weight: Optional[str] = None
    silver_weight: Optional[str] = None
    status: str = "SUBMITTED"
    created_at: datetime
    uploaded_at: datetime

    @field_serializer('created_at', 'uploaded_at')
    def serialize_datetime(self, dt: datetime, _info):
        from datetime import timezone
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    class Config:
        from_attributes = True

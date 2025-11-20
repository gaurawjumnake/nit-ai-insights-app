from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional, List
from datetime import datetime

class AccountBase(BaseModel):
    name: str = Field(..., description="The client account name.")
    delivery_unit_id: UUID = Field(..., description="Foreign key linking to the Delivery Unit.")
    account_manager: Optional[str] = None
    customer_overview: Optional[str] = None
    ai_recommendations: Optional[str] = None

class AccountCreate(AccountBase):
    pass

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    delivery_unit_id: Optional[UUID] = None
    account_manager: Optional[str] = None
    customer_overview: Optional[str] = None
    ai_recommendations: Optional[str] = None

class DeliveryUnitOut(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True

class ProjectOut(BaseModel):
    id: UUID
    name: str
    status: Optional[str] = None
    overview: Optional[str] = None
    expected_revenue: Optional[float] = 0.0
    total_ai_revenue: Optional[float] = 0.0
    ai_direct_hours: Optional[float] = 0.0
    ai_assist_hours: Optional[float] = 0.0
    ytd_revenue: Optional[float] = None
    project_type: Optional[str] = None
    tech_stack: Optional[List[str]] = None

    class Config:
        from_attributes = True

class AccountOut(AccountBase):
    id: UUID
    created_at: datetime
    delivery_unit: DeliveryUnitOut
    project_count: int
    total_revenue: float
    ai_revenue: float
    ai_penetration_pct: float
    total_ai_hours: float
    active_project_count: int
    inactive_project_count: int
    projects: List[ProjectOut] = []

    class Config:
        from_attributes = True

class AccountCreateResponse(AccountBase):
    id: UUID
    delivery_unit_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

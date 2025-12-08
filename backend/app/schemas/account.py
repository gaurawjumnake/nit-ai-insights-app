from pydantic import BaseModel, Field, computed_field
from uuid import UUID
from typing import Optional, List
from datetime import datetime
from ..schemas.project import ProjectOut

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

class AccountOut(AccountBase):
    id: UUID
    created_at: datetime
    delivery_unit: DeliveryUnitOut
    project_count: int
    total_revenue: float
    ai_revenue: float
    total_ai_hours: float
    active_project_count: int
    inactive_project_count: int
    projects: List[ProjectOut] = []

    @computed_field
    @property
    def ai_penetration_pct(self) -> float:
        total_rev = self.total_revenue or 0
        ai_rev = self.ai_revenue or 0
        if total_rev > 0 and ai_rev > 0:
            return (ai_rev / total_rev) * 100
        return 0.0

    class Config:
        from_attributes = True

class AccountCreateResponse(AccountBase):
    id: UUID
    delivery_unit_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

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


class AccountRevenueSummary(BaseModel):
    """Account-level revenue summary for charts and dashboards."""
    account_id: UUID
    account_name: str
    delivery_unit_name: Optional[str] = None
    project_count: int = 0
    active_project_count: int = 0
    inactive_project_count: int = 0
    total_revenue: float = 0.0
    total_ai_direct_revenue: float = 0.0
    total_ai_assisted_revenue: float = 0.0
    total_expected_revenue: float = 0.0
    total_ytd_revenue: float = 0.0
    total_ai_hours: float = 0.0
    
    @computed_field
    @property
    def total_ai_revenue(self) -> float:
        """Sum of AI direct and assisted revenue."""
        return self.total_ai_direct_revenue + self.total_ai_assisted_revenue
    
    @computed_field
    @property
    def ai_penetration_pct(self) -> float:
        """AI revenue as percentage of total revenue."""
        if self.total_revenue > 0:
            return (self.total_ai_revenue / self.total_revenue) * 100
        return 0.0
    
    class Config:
        from_attributes = True

from pydantic import BaseModel, Field, computed_field
from typing import Optional
from uuid import UUID
from datetime import datetime


class RevenueBase(BaseModel):
    project_id: UUID = Field(..., description="Foreign key linking to the Project.")
    project_name: str = Field(..., description="The project name.")
    expected_revenue: Optional[float] = 0.0
    ytd_revenue: Optional[float] = 0.0
    ai_direct_revenue: Optional[float] = 0.0
    ai_direct_people: Optional[int] = 0
    ai_assisted_people: Optional[int] = 0
    ai_assisted_revenue: Optional[float] = 0.0
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    status: Optional[str] = "active"
    total_ai_revenue: Optional[float] = 0.0
    total_revenue: Optional[float] = 0.0
    collection_date: Optional[datetime] = None


class RevenueCreate(RevenueBase):
    pass


class RevenueUpdate(BaseModel):
    project_name: Optional[str] = None
    expected_revenue: Optional[float] = None
    ytd_revenue: Optional[float] = None
    ai_direct_revenue: Optional[float] = None
    ai_direct_people: Optional[int] = None
    ai_assisted_people: Optional[int] = None
    ai_assisted_revenue: Optional[float] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    status: Optional[str] = None
    total_ai_revenue: Optional[float] = None
    total_revenue: Optional[float] = None
    collection_date: Optional[datetime] = None


class ProjectOut(BaseModel):
    id: UUID
    name: str
    account_id: UUID
    
    class Config:
        from_attributes = True


class RevenueOut(RevenueBase):
    id: UUID
    created_at: Optional[datetime] = None
    project: Optional[ProjectOut] = None

    @computed_field
    @property
    def ai_penetration(self) -> float:
        """Calculate AI revenue penetration percentage."""
        total_rev = self.total_revenue or 0
        ai_rev = self.total_ai_revenue or 0  # type: ignore
        if total_rev > 0 and ai_rev > 0:
            return (ai_rev / total_rev) * 100  
        return 0.0

    class Config:
        from_attributes = True


class RevenueSummary(BaseModel):
    """Summary statistics for revenue data."""
    revenue_id: UUID
    project_id: UUID
    project_name: str
    account_id: Optional[UUID] = None
    account_name: Optional[str] = None
    delivery_unit_name: Optional[str] = None
    expected_revenue: float
    ytd_revenue: float
    ai_direct_revenue: float
    ai_assisted_revenue: float
    total_ai_revenue: float
    total_revenue: float
    ai_direct_people: int
    ai_assisted_people: int
    status: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    month: Optional[int] = None
    year: Optional[int] = None
    collection_date: Optional[datetime] = None

    
    @computed_field
    @property
    def ai_penetration(self) -> float:
        """Calculate AI revenue penetration percentage."""
        total_rev = self.total_revenue or 0
        ai_rev = self.total_ai_revenue or 0  # type: ignore
        if total_rev > 0 and ai_rev > 0:
            return (ai_rev / total_rev) * 100
        return 0.0
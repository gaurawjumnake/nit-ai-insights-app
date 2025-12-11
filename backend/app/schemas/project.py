from pydantic import BaseModel, Field, computed_field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class ProjectBase(BaseModel):
    name: str = Field(..., description="The project name.")
    account_id: UUID = Field(..., description="Foreign key linking to the Account.")
    delivery_unit_id: UUID = Field(..., description="Foreign key linking to the Account.")
    overview: Optional[str] = None
    status: Optional[str] = "active"
    # ai_direct_people: Optional[int] = 0
    ai_direct_hours: Optional[float] = 0.0
    ai_assist_hours: Optional[float] = 0.0
    tech_stack: Optional[List[str]] = None
    ai_recommendations: Optional[str] = None
    project_type: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    proposal_end_date: Optional[datetime] = None
    expected_win_date: Optional[datetime] = None
    expected_outcome: Optional[str] = None
    code_coverage_pct: Optional[float] = 0.0


class ProjectCreate(ProjectBase):
    expected_revenue: Optional[float] = 0.0
    ytd_revenue: Optional[float] = 0.0
    ai_revenue: Optional[float] = 0.0
    ai_assisted_revenue: Optional[float] = 0.0
    ai_direct_people: Optional[int] = 0
    ai_assisted_people: Optional[int] = 0
    total_ai_revenue: Optional[float] = 0.0
    total_revenue: Optional[float] = 0.0


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    overview: Optional[str] = None
    status: Optional[str] = None
    # ai_direct_people: Optional[int] = None
    ai_direct_hours: Optional[float] = None
    ai_assist_hours: Optional[float] = None
    tech_stack: Optional[List[str]] = None
    ai_recommendations: Optional[str] = None
    project_type: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    proposal_end_date: Optional[datetime] = None
    expected_win_date: Optional[datetime] = None
    expected_outcome: Optional[str] = None
    code_coverage_pct: Optional[float] = None
    expected_revenue: Optional[float] = None
    ytd_revenue: Optional[float] = None
    ai_revenue: Optional[float] = None
    ai_assisted_revenue: Optional[float] = None
    ai_direct_people: Optional[int] = None
    ai_assisted_people: Optional[int] = None
    total_ai_revenue: Optional[float] = None
    total_revenue: Optional[float] = None


class AccountOut(BaseModel):
    id: UUID
    name: str
    
    class Config:
        from_attributes = True


class ProjectOut(ProjectBase):
    id: UUID
    created_at: Optional[datetime] = None
    account: Optional[AccountOut] = None
    expected_revenue: Optional[float] = 0.0
    ytd_revenue: Optional[float] = 0.0
    ai_revenue: Optional[float] = 0.0  
    ai_assisted_revenue: Optional[float] = 0.0
    total_ai_revenue: Optional[float] = 0.0
    total_revenue: Optional[float] = 0.0
    
    @computed_field
    @property
    def ai_penetration(self) -> float:
        """AI revenue as a percentage of total revenue."""
        total_rev = self.total_revenue or 0
        ai_total = (self.ai_revenue or 0) + (self.ai_assisted_revenue or 0)
        if total_rev > 0 and ai_total > 0:
            return (ai_total / total_rev) * 100
        return 0.0

    class Config:
        from_attributes = True


class ProjectSummary(BaseModel):
    """Summary statistics for project data with revenue information."""
    project_id: UUID
    project_name: str
    account_id: Optional[UUID] = None
    account_name: Optional[str] = None
    delivery_unit_name: Optional[str] = None
    total_ai_direct_hours: float = 0.0
    total_ai_assist_hours: float = 0.0
    ai_direct_people: Optional[int] = 0
    project_status: Optional[str] = None
    project_type: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    total_expected_rev: float = 0.0
    total_ytd_rev: float = 0.0
    total_ai_rev: float = 0.0
    total_ai_assist_rev: float = 0.0
    total_revenue: float = 0.0
    total_project_count: int = 1
    month: Optional[int] = None
    year: Optional[int] = None
    
    @computed_field
    @property
    def ai_penetration(self) -> float:
        """Calculate AI revenue penetration percentage."""
        total_rev = self.total_revenue or 0
        total_ai = (self.total_ai_rev or 0) + (self.total_ai_assist_rev or 0)
        if total_rev > 0 and total_ai > 0:
            return (total_ai / total_rev) * 100
        return 0.0

class ProjectExport(BaseModel):
    name: str = Field(..., description="The project name.")
    account_id: UUID = Field(..., description="Foreign key linking to the Account.")
    delivery_unit_id: UUID = Field(..., description="Foreign key linking to the Account.")
    overview: Optional[str] = None
    status: Optional[str] = "active"
    delivery_uni_name: Optional[str] = None
    account_name: Optional[str] = None
    # ai_direct_people: Optional[int] = 0
    ai_direct_hours: Optional[float] = 0.0
    ai_assist_hours: Optional[float] = 0.0
    tech_stack: Optional[List[str]] = None
    ai_recommendations: Optional[str] = None
    project_type: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    proposal_end_date: Optional[datetime] = None
    expected_win_date: Optional[datetime] = None
    expected_outcome: Optional[str] = None
    code_coverage_pct: Optional[float] = 0.0
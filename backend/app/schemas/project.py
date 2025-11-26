from pydantic import BaseModel, Field, computed_field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class ProjectBase(BaseModel):
    name: str = Field(..., description="The project name.")
    account_id: UUID = Field(..., description="Foreign key linking to the Account.")
    overview: Optional[str] = None
    status: Optional[str] = "active"
    expected_revenue: Optional[float] = 0.0
    ytd_revenue: Optional[float] = 0.0
    ai_revenue: Optional[float] = 0.0  
    ai_assisted_revenue: Optional[float] = 0.0 
    total_revenue: Optional[float] = 0.0
    total_ai_revenue: Optional[float] = 0.0
    ai_direct_people: Optional[float] = 0.0
    ai_assisted_people: Optional[float] = 0.0
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
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    overview: Optional[str] = None
    status: Optional[str] = None
    expected_revenue: Optional[float] = None
    ytd_revenue: Optional[float] = None
    ai_revenue: Optional[float] = None
    ai_assisted_revenue: Optional[float] = None
    total_revenue: Optional[float] = None
    total_ai_revenue: Optional[float] = None
    ai_direct_people: Optional[float] = None
    ai_assisted_people: Optional[float] = None
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


class AccountOut(BaseModel):
    id: UUID
    name: str
    
    class Config:
        from_attributes = True


class ProjectOut(ProjectBase):
    id: UUID
    created_at: Optional[datetime] = None
    account: Optional[AccountOut] = None

    @computed_field
    @property
    def ai_penetration(self) -> float:
        if self.total_revenue and self.total_revenue > 0:
            return (self.total_ai_revenue / self.total_revenue) * 100
        return 0.0

    class Config:
        from_attributes = True



class ProjectSummary(BaseModel):
    project_id: UUID
    project_name: str
    account_id: Optional[UUID]
    account_name: Optional[str]
    delivery_unit_name: Optional[str]
    total_expected_rev: float
    total_ytd_rev: float
    total_ai_rev: float
    total_ai_assist_rev: float
    total_ai_direct_hours: float
    total_ai_assist_hours: float
    total_project_count: int
    month: Optional[int]
    year: Optional[int]
    total_revenue: Optional[float] = 0.0
    project_status: Optional[str] = None
    project_type: Optional[str] = None

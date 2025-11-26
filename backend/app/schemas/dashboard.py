from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID

from backend.app.schemas.project import ProjectSummary

class DashboardStatsOut(BaseModel):
    total_accounts: int
    active_accounts: int
    inactive_accounts: int
    total_projects: int
    active_projects: int
    non_active_projects: int
    total_revenue: float
    active_revenue: float
    non_active_revenue: float
    total_ai_assisted_revenue: float
    total_ai_direct_revenue: float
    project_bifurcation: List[dict]
    projects: List[ProjectSummary]

from typing import List, Optional
from pydantic import BaseModel, computed_field
from uuid import UUID

from backend.app.schemas.project import ProjectSummary

class DashboardStatsOut(BaseModel):
    """Dashboard statistics with project and revenue metrics."""
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
    delivery_unit_name: Optional[str] = None
    
    @computed_field
    @property
    def total_ai_revenue(self) -> float:
        """Calculate total AI revenue (direct + assisted)."""
        return self.total_ai_direct_revenue + self.total_ai_assisted_revenue
    
    @computed_field
    @property
    def ai_penetration_pct(self) -> float:
        """Calculate AI revenue penetration percentage."""
        total_rev = self.total_revenue or 0
        ai_rev = self.total_ai_revenue or 0
        if total_rev > 0 and ai_rev > 0:
            return (ai_rev / total_rev) * 100
        return 0.0

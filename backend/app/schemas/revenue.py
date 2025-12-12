from pydantic import BaseModel, Field, computed_field,field_validator,model_validator
import math
from typing import Optional,Any
from uuid import UUID
from datetime import datetime
from backend.app.schemas.account import AccountOut
from backend.app.schemas.delivery_unit import DeliveryUnitOut
from backend.app.schemas.project import ProjectOut
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
    @field_validator(
    'expected_revenue', 
    'ytd_revenue', 
    'ai_direct_revenue', 
    'ai_assisted_revenue', 
    'total_ai_revenue', 
    'total_revenue', 
    check_fields=False
    )
    @classmethod
    def sanitize_nan(cls, v):
        # Check if value is not None and matches NaN or Infinity
        if v is not None and (math.isnan(v) or math.isinf(v)):
            return 0.0  # Or return None if you prefer null in JSON
        return v

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


# class ProjectOut(BaseModel):
#     id: UUID
#     name: str
#     account_id: UUID

#     class Config:
#         from_attributes = True


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

class RevenueExport(RevenueBase):
    """
    Schema for exporting revenue data with flattened Account and Delivery Unit names.
    """
    id: UUID
    project_id: UUID = Field(..., description="Foreign key linking to the Project.")
    
    # We allow this to be None initially, then populate it via validator
    project_name: Optional[str] = Field(default=None, description="The project name.")

    # 1. THE BRIDGE: Capture the nested Project data (Hidden from JSON output)
    # This reads the 'project' relationship from the database result.
    project_data: Optional[ProjectOut] = Field(default=None, alias="project", exclude=True)

    # 2. COMPUTED FIELDS: Extract names from the bridge
    @computed_field
    @property
    def account_name(self) -> Optional[str]:
        # Path: Revenue -> Project -> Account -> Name
        if self.project_data and self.project_data.account:
            return self.project_data.account.name
        return None

    @computed_field
    @property
    def delivery_unit_name(self) -> Optional[str]:
        # Path: Revenue -> Project -> DeliveryUnit -> Name
        if self.project_data and self.project_data.delivery_unit:
            return self.project_data.delivery_unit.name
        return None

    @computed_field
    @property
    def ai_penetration(self) -> float:
        total_rev = self.total_revenue or 0.0
        ai_rev = self.total_ai_revenue or 0.0
        if total_rev > 0 and ai_rev > 0:
            return (ai_rev / total_rev) * 100  
        return 0.0

    # 3. POPULATE NAMES: Ensure project_name is filled
    @model_validator(mode='after')
    def populate_names(self):
        if self.project_data:
            self.project_name = self.project_data.name
        return self

    # 4. NAN HANDLING
    @field_validator(
        'expected_revenue', 
        'ytd_revenue', 
        'ai_direct_revenue', 
        'ai_assisted_revenue', 
        'total_ai_revenue', 
        'total_revenue', 
        check_fields=False,
        mode='before'
    )
    @classmethod
    def sanitize_nan(cls, v):
        if v is None:
            return 0.0
        try:
            float_val = float(v)
            if math.isnan(float_val) or math.isinf(float_val):
                return 0.0
            return float_val
        except (TypeError, ValueError):
            return 0.0

    class Config:
        from_attributes = True
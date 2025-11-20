from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class RevMaster(BaseModel):
    id : UUID = Field(..., description="master tabel unique id")
    account_id: UUID = Field(..., description="Foreign key linking to the Account.")
    project_id: UUID = Field(..., description="Foreign key linking to the Account.")
    account_name: str
    project_name: str

    total_rev : float
    total_ai_direct_rev: float
    total_ai_assist_rev: float
    expected_rev: float

    ai_direct_hours: float
    ai_assist_hours: float
    total_ai_hours: float

    project_status: float
    project_type: str
    month: datetime
    year: datetime





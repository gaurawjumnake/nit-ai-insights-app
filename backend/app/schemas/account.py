from pydantic import BaseModel, Field
from pydantic.types import UUID
from typing import Optional, List
from datetime import datetime

# Base schema for shared attributes (used for creation/update)
class AccountBase(BaseModel):
    name: str = Field(..., description="The client account name.")
    delivery_unit_id: str = Field(..., description="Foreign key linking to the Delivery Unit.")
    account_manager: Optional[str] = None
    customer_overview: Optional[str] = None
    ai_recommendations: Optional[str] = None

# Schema for creating a new account (all fields required based on AccountBase)
class AccountCreate(AccountBase):
    pass

# Schema for updating an account (all fields are optional)
class AccountUpdate(BaseModel):
    name: Optional[str] = None
    delivery_unit_id: Optional[str] = None
    account_manager: Optional[str] = None
    customer_overview: Optional[str] = None
    ai_recommendations: Optional[str] = None

# Schema for data returned to the user (Response Model)
class AccountOut(AccountBase):
    id: UUID
    delivery_unit_id: UUID
    created_at: datetime

    class Config:
        # Enables conversion from ORM object (like SQLAlchemy) to Pydantic object
        from_attributes = True

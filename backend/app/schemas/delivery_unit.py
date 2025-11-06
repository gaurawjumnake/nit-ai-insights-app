from pydantic import BaseModel
from pydantic.types import UUID
from datetime import datetime

class DeliveryUnitOut(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    class Config:
        from_attributes = True

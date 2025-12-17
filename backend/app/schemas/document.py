from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class ProjectDocumentOut(BaseModel):
    id: UUID
    project_id : UUID
    content : Optional[str] = None
    document_type : Optional[str] = None
    created_at : datetime

    class Config:
        from_attributes = True

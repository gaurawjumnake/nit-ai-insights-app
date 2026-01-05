from sqlalchemy import Column, String, DateTime,text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.db.base import Base 
from datetime import datetime, timezone, timedelta
import uuid

IST = timezone(timedelta(hours=5, minutes=30))

class ProjectDocument(Base):
    __tablename__ = "project_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=text("gen_random_uuid()"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    content = Column(String, index=True, nullable=True)
    document_type = Column(String, index=True, nullable=True)
    created_at = Column(DateTime(timezone=False), default=lambda: datetime.now(IST).replace(tzinfo=None))
    project = relationship("Project", back_populates="project_documents")
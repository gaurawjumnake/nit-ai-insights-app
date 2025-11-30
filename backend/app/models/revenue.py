import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from backend.app.db.base import Base


class RevenueMaster(Base):
    __tablename__ = "revenue_master"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    project_name = Column(String)
    expected_revenue = Column(Numeric)
    ytd_revenue = Column(Numeric)
    ai_direct_revenue = Column(Numeric)
    ai_direct_people = Column(Integer)
    ai_assisted_people = Column(Integer)
    ai_assisted_revenue = Column(Numeric)
    from_date = Column(DateTime)
    to_date = Column(DateTime)
    status = Column(String)
    total_ai_revenue = Column(Numeric)
    total_revenue = Column(Numeric)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="revenues")
import uuid
from sqlalchemy import Column, String, Float, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from backend.app.db.base import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    account_id = Column(UUID, ForeignKey("accounts.id"), nullable=False)
    overview = Column(Text)
    status = Column(String, default="active")
    expected_revenue = Column(Float, default=0.0)
    ytd_revenue = Column(Float, default=0.0)
    ai_revenue = Column(Float, default=0.0)  
    ai_assisted_revenue = Column(Float, default=0.0)  
    total_revenue = Column(Float, default=0.0) 
    total_ai_revenue = Column(Float, default=0.0)
    ai_direct_people = Column(Float, default=0.0)
    ai_assisted_people = Column(Float, default=0.0)
    ai_direct_hours = Column(Float, default=0.0)
    ai_assist_hours = Column(Float, default=0.0)
    tech_stack = Column(JSONB)
    ai_recommendations = Column(Text)
    project_type = Column(String, default="Undefined")
    from_date = Column(DateTime)
    to_date = Column(DateTime)
    proposal_end_date = Column(DateTime)
    expected_win_date = Column(DateTime)
    expected_outcome = Column(Text)
    code_coverage_pct = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    account = relationship("Account", back_populates="projects")

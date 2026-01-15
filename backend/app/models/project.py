import uuid
from sqlalchemy import Column, String, Float, ForeignKey, Text, DateTime, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from backend.app.db.base import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    delivery_unit_id = Column(UUID(as_uuid=True), ForeignKey("delivery_units.id"), nullable=False)
    overview = Column(Text)
    status = Column(String, default="active")
    # ai_direct_people = Column(Integer, default=0)
    ai_direct_hours = Column(Float, default=0.0)
    ai_assist_hours = Column(Float, default=0.0)
    tech_stack = Column(JSONB)
    ai_recommendations = Column(Text)
    ai_recommendations_generated_at = Column(DateTime)
    project_type = Column(String)
    from_date = Column(DateTime)
    to_date = Column(DateTime)
    proposal_end_date = Column(DateTime)
    expected_win_date = Column(DateTime)
    expected_outcome = Column(Text)
    technical_roadmap = Column(Text)
    product_roadmap = Column(Text)
    code_coverage_pct = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    
    # Relationships
    account = relationship("Account", back_populates="projects")
    revenues = relationship("RevenueMaster", back_populates="project", cascade="all, delete-orphan")
    delivery_unit = relationship("DeliveryUnit", back_populates="projects", )
    project_documents = relationship("ProjectDocument", back_populates="project")

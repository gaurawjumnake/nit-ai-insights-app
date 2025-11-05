import uuid
from sqlalchemy import Column, String, Float, ForeignKey, Text, ARRAY
from sqlalchemy.orm import relationship
from ..db.base import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    account_id = Column(String, ForeignKey("accounts.id"), nullable=False)
    overview = Column(Text)
    status = Column(String)
    ytd_revenue = Column(Float, default=0.0)
    total_ai_revenue = Column(Float, default=0.0)
    ai_direct_hours = Column(Float, default=0.0)
    ai_assist_hours = Column(Float, default=0.0)
    tech_stack = Column(ARRAY(String))
    
    account = relationship("Account", back_populates="projects")

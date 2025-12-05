from sqlalchemy import Column, String, DateTime,text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.db.base import Base 
from datetime import datetime
import uuid

class DeliveryUnit(Base):
    __tablename__ = "delivery_units"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=text("gen_random_uuid()"))
    name = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    accounts = relationship("Account", back_populates="delivery_unit")
    projects = relationship("Project", back_populates="delivery_unit")

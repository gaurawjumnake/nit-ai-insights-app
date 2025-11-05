from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..db.base import Base 

class DeliveryUnit(Base):
    __tablename__ = "delivery_units"

    id = Column(UUID, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    
    # Relationship back to Accounts
    accounts = relationship("Account", back_populates="delivery_unit")

from sqlalchemy.orm import Session
from typing import List, Optional

from ..models.delivery_unit import DeliveryUnit

def get_delivery_units(db: Session, skip: int = 0, limit: int = 100) -> List[DeliveryUnit]:
    """Retrieve a list of delivery units."""
    return db.query(DeliveryUnit).offset(skip).limit(limit).all()

def get_delivery_unit(db: Session, delivery_unit_id: str) -> Optional[DeliveryUnit]:
    """Retrieve a single delivery unit by ID."""
    return db.query(DeliveryUnit).filter(DeliveryUnit.id == delivery_unit_id).first()

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.app.schemas.delivery_unit import DeliveryUnitOut
from backend.app.services import delivery_unit as delivery_unit_service
from backend.app.db.session import get_db

router = APIRouter(
    prefix="/delivery_units",
    tags=["Delivery Units"],
)

@router.get("/", response_model=List[DeliveryUnitOut])
def read_delivery_units(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Retrieve a list of all delivery units.
    """
    delivery_units = delivery_unit_service.get_delivery_units(db, skip=skip, limit=limit)
    return delivery_units

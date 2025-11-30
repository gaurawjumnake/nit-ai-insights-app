from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID
from uuid import UUID as _UUID
from sqlalchemy.exc import IntegrityError

from backend.app.models.revenue import RevenueMaster
from backend.app.schemas.revenue import RevenueUpdate


def get_revenues(db: Session, skip: int = 0, limit: int = 100) -> List[RevenueMaster]:
    """Retrieve a list of all revenue records."""
    return db.query(RevenueMaster).options(joinedload(RevenueMaster.project)).all()


def get_revenue(db: Session, revenue_id: UUID) -> Optional[RevenueMaster]:
    """Retrieve a single revenue record by ID."""
    return db.query(RevenueMaster).options(
        joinedload(RevenueMaster.project)
    ).filter(RevenueMaster.id == revenue_id).first()


def get_revenues_by_project(db: Session, project_id: UUID) -> List[RevenueMaster]:
    """Retrieve all revenue records for a specific project."""
    return db.query(RevenueMaster).filter(
        RevenueMaster.project_id == project_id
    ).all()


def get_revenue_by_project_id(db: Session, project_id: UUID) -> Optional[RevenueMaster]:
    """Retrieve the latest revenue record for a project."""
    return db.query(RevenueMaster).filter(
        RevenueMaster.project_id == project_id
    ).order_by(RevenueMaster.created_at.desc()).first()


def _sanitize_revenue_payload(revenue_dict: dict) -> dict:
    """Coerce incoming payload to the correct types that match the DB schema."""
    from datetime import datetime
    from decimal import Decimal

    def parse_dt(value):
        if value in (None, "", "null"):
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value)
        except Exception:
            try:
                return datetime.strptime(value, "%Y-%m-%d")
            except Exception:
                return None

    # Convert numeric fields to Decimal for precision
    for key in [
        "expected_revenue",
        "ytd_revenue",
        "ai_direct_revenue",
        "ai_assisted_revenue",
        "total_ai_revenue",
        "total_revenue",
    ]:
        if key in revenue_dict and revenue_dict[key] is not None:
            try:
                revenue_dict[key] = Decimal(str(revenue_dict[key]))
            except Exception:
                revenue_dict[key] = Decimal('0.0')

    # Convert integer fields
    for key in ["ai_direct_people", "ai_assisted_people"]:
        if key in revenue_dict and revenue_dict[key] is not None:
            try:
                revenue_dict[key] = int(revenue_dict[key])
            except Exception:
                revenue_dict[key] = 0

    # Parse dates
    for key in ["from_date", "to_date"]:
        if key in revenue_dict:
            revenue_dict[key] = parse_dt(revenue_dict[key])

    # Convert project_id to UUID
    proj_id = revenue_dict.get("project_id")
    if proj_id is not None:
        try:
            revenue_dict["project_id"] = _UUID(str(proj_id))
        except Exception:
            pass

    return revenue_dict


def update_revenue(db: Session, revenue_id: UUID, revenue_data: RevenueUpdate) -> Optional[RevenueMaster]:
    """Update an existing revenue record by ID."""
    db_revenue = get_revenue(db, revenue_id)
    if db_revenue:
        update_data = revenue_data.model_dump(exclude_unset=True)
        update_data = _sanitize_revenue_payload(update_data)
        
        # Recalculate total_ai_revenue if ai_revenue or ai_assisted_revenue changed
        if 'ai_direct_revenue' in update_data or 'ai_assisted_revenue' in update_data:
            ai_direct = update_data.get('ai_direct_revenue', db_revenue.ai_revenue) or 0
            ai_assisted = update_data.get('ai_assisted_revenue', db_revenue.ai_assisted_revenue) or 0
            update_data['total_ai_revenue'] = ai_direct + ai_assisted
        
        for key, value in update_data.items():
            setattr(db_revenue, key, value)
        
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise ValueError("Invalid update: foreign key or data type issue") from e
        db.refresh(db_revenue)
        return db_revenue
    return None


def delete_revenue(db: Session, revenue_id: UUID) -> bool:
    """Delete a revenue record by ID."""
    db_revenue = get_revenue(db, revenue_id)
    if db_revenue:
        db.delete(db_revenue)
        db.commit()
        return True
    return False


def delete_revenues_by_project(db: Session, project_id: UUID) -> int:
    """Delete all revenue records for a specific project. Returns count of deleted records."""
    count = db.query(RevenueMaster).filter(
        RevenueMaster.project_id == project_id
    ).delete(synchronize_session=False)
    db.commit()
    return count
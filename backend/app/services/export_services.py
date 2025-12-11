from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from typing import List, Optional
from backend.app.models.project import Project
from backend.app.models.account import Account
from backend.app.models.revenue import RevenueMaster
from backend.app.schemas.revenue import RevenueExport


def get_projects(db: Session, skip: int = 0, limit: int = 100) -> List[Project]:
    """Retrieve a list of all projects."""
    return db.query(Project).options(joinedload(Project.account)).all()


def get_revenues_2(db: Session, skip: int = 0, limit: int = 100) -> List[RevenueMaster]:
    """Retrieve a list of all revenue records."""
    return db.query(RevenueMaster).options(joinedload(RevenueMaster.project)).all()

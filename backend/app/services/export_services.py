from sqlalchemy.orm import Session, joinedload, contains_eager
from typing import List, Optional, Tuple
from backend.app.models.project import Project
from backend.app.models.revenue import RevenueMaster
from backend.doc_insighter.tools.app_logger import Logger
log = Logger()

from uuid import UUID
from sqlalchemy import cast

def get_projects(db: Session, skip: int = 0, limit: int = 100) -> List[Project]: 
    """Retrieve a list of all projects with their associated delivery unit."""

    query = db.query(Project)\
        .join(Project.account)\
        .join(Project.delivery_unit)
    query = query.options(
        contains_eager(Project.account),
        contains_eager(Project.delivery_unit)
    )
    log.log_info(f"Project data exported successfully")
    return query.order_by(Project.name).all()

def get_revenues(db: Session, skip: int = 0, limit: int = 100, account_id: Optional[UUID] = None) -> List[RevenueMaster]:
    """Retrieve a list of all revenue records."""
    query = db.query(RevenueMaster)\
        .join(RevenueMaster.project)\
        .join(Project.account)\
        .join(Project.delivery_unit)

    if account_id:
        query = query.filter(Project.account_id == account_id)

        query = query.options(
        contains_eager(RevenueMaster.project).contains_eager(Project.account),
        contains_eager(RevenueMaster.project).contains_eager(Project.delivery_unit)
    )
    log.log_info(f"Revenue master data exported successfully")
    return query.order_by(Project.name).all()
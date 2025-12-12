from sqlalchemy.orm import Session, joinedload, contains_eager
from typing import List, Optional, Tuple
from backend.app.models.project import Project
from backend.app.schemas.project import ProjectSummary,ProjectExport
from backend.app.models.account import Account
from backend.app.models.revenue import RevenueMaster
from backend.app.models.delivery_unit import DeliveryUnit
from uuid import UUID
from sqlalchemy import cast

def get_projects(db: Session, skip: int = 0, limit: int = 100) -> List[Project]:
    
    """Retrieve a list of all projects with their associated delivery unit."""
    
    # -------------------------------
    # return db.query(Project)\
    #     .options(joinedload(Project.account).joinedload(Account.delivery_unit))\
    #     .all()
    # -------------------------------
    query = db.query(Project)\
        .join(Project.account)\
        .join(Project.delivery_unit)
    query = query.options(
        contains_eager(Project.account),
        contains_eager(Project.delivery_unit)
    )
    return query.order_by(Project.name).all()

def get_revenues(db: Session, skip: int = 0, limit: int = 100,account_id: Optional[UUID] = None) -> List[RevenueMaster]:
    """Retrieve a list of all revenue records."""
    #--------------------------------------
    # query = db.query(RevenueMaster)

    # # 2. Filter Logic: Only join and filter if account_id is provided
    # if account_id:
    #     query = query.join(RevenueMaster.project).filter(Project.account_id == account_id)

    # # 3. Eager Load Logic:
    # # We need to traverse: Revenue -> Project -> Account
    # # AND:                 Revenue -> Project -> DeliveryUnit
    # query = query.options(
    #     joinedload(RevenueMaster.project).joinedload(Project.account),
    #     joinedload(RevenueMaster.project).joinedload(Project.delivery_unit)
    # )

    # # 4. Execute
    # return query.order_by(Project.name).all()
    #--------------------------------------
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
    return query.order_by(Project.name).all()
from sqlalchemy.orm import Session, joinedload, aliased
from sqlalchemy import func, case
from typing import List, Optional
import logging
from uuid import UUID

from sqlalchemy.orm import Session, joinedload, aliased
from sqlalchemy import func, case
from typing import List, Optional
import logging
from uuid import UUID

from ..models.account import Account
from ..models.delivery_unit import DeliveryUnit
from ..models.project import Project
from ..schemas.account import AccountCreate, AccountUpdate

logging.basicConfig(level=logging.DEBUG)


def get_accounts(db: Session, skip: int = 0, limit: int = 100) -> List[Account]:
    """
    Retrieve a list of accounts with aggregated project metrics calculated via subqueries.
    """
    project_metrics = db.query(
        Project.account_id,
        func.count(Project.id).label("project_count"),
        func.sum(case((Project.status == 'active', 1), else_=0)).label("active_project_count"),
        func.sum(case((Project.status == 'inactive', 1), else_=0)).label("inactive_project_count"),
        func.sum(Project.expected_revenue + Project.total_ai_revenue).label("total_revenue"),
        func.sum(Project.total_ai_revenue).label("ai_revenue"),
        func.sum(Project.ai_direct_hours + Project.ai_assist_hours).label("total_ai_hours")
    ).group_by(Project.account_id).subquery()

    project_metrics_alias = aliased(project_metrics, name="project_metrics")

    accounts_query = db.query(
        Account,
        project_metrics_alias.c.project_count,
        project_metrics_alias.c.active_project_count,
        project_metrics_alias.c.inactive_project_count,
        project_metrics_alias.c.total_revenue,
        project_metrics_alias.c.ai_revenue,
        project_metrics_alias.c.total_ai_hours
    ).outerjoin(
        project_metrics_alias, Account.id == project_metrics_alias.c.account_id
    ).options(
        joinedload(Account.delivery_unit)
    ).order_by(
        Account.created_at.desc()
    )

    results = accounts_query.offset(skip).limit(limit).all()

    accounts_with_metrics = []
    for account, project_count, active_count, inactive_count, total_rev, ai_rev, ai_hours in results:
        account.project_count = project_count or 0
        account.active_project_count = active_count or 0
        account.inactive_project_count = inactive_count or 0
        account.total_revenue = total_rev or 0.0
        account.ai_revenue = ai_rev or 0.0
        account.total_ai_hours = ai_hours or 0.0
        account.ai_penetration_pct = (account.ai_revenue / account.total_revenue * 100) if account.total_revenue > 0 else 0.0
        accounts_with_metrics.append(account)

    return accounts_with_metrics

def get_account(db: Session, account_id: UUID) -> Optional[Account]:
    """
    Retrieve a single account by ID with its projects and calculated metrics.
    """
    project_metrics = db.query(
        Project.account_id,
        func.count(Project.id).label("project_count"),
        func.sum(case((Project.status == 'active', 1), else_=0)).label("active_project_count"),
        func.sum(case((Project.status == 'inactive', 1), else_=0)).label("inactive_project_count"),
        func.sum(Project.expected_revenue + Project.total_ai_revenue).label("total_revenue"),
        func.sum(Project.total_ai_revenue).label("ai_revenue"),
        func.sum(Project.ai_direct_hours + Project.ai_assist_hours).label("total_ai_hours")
    ).filter(Project.account_id == account_id).group_by(Project.account_id).subquery()

    metrics = aliased(project_metrics, name="metrics")

    result = db.query(
        Account,
        metrics.c.project_count,
        metrics.c.active_project_count,
        metrics.c.inactive_project_count,
        metrics.c.total_revenue,
        metrics.c.ai_revenue,
        metrics.c.total_ai_hours
    ).outerjoin(
        metrics, Account.id == metrics.c.account_id
    ).options(
        joinedload(Account.delivery_unit),
        joinedload(Account.projects)
    ).filter(Account.id == account_id).first()

    if not result:
        return None

    account, project_count, active_count, inactive_count, total_rev, ai_rev, ai_hours = result

    account.project_count = project_count or 0
    account.active_project_count = active_count or 0
    account.inactive_project_count = inactive_count or 0
    account.total_revenue = total_rev or 0.0
    account.ai_revenue = ai_rev or 0.0
    account.total_ai_hours = ai_hours or 0.0
    account.ai_penetration_pct = (account.ai_revenue / account.total_revenue * 100) if account.total_revenue > 0 else 0.0
    
    return account

def create_account(db: Session, account_data: AccountCreate) -> Account:
    """Create a new account record."""
    logging.debug(f"Creating account with data: {account_data}")
    try:
        db_account = Account(**account_data.model_dump())
        db.add(db_account)
        db.commit()
        db.refresh(db_account)
        return db_account
    except Exception as e:
        logging.error(f"Error creating account: {e}")
        raise

def update_account(db: Session, account_id: UUID, account_data: AccountUpdate) -> Optional[Account]:
    """Update an existing account by ID."""
    db_account = get_account(db, account_id)
    if db_account:
        update_data = account_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_account, key, value)
        
        db.commit()
        db.refresh(db_account)
        return db_account
    return None

def delete_account(db: Session, account_id: UUID) -> bool:
    """Delete an account by ID."""
    db_account = db.query(Account).filter(Account.id == account_id).first()
    if not db_account:
        return False

    db.query(Project).filter(Project.account_id == account_id).delete(synchronize_session=False)
    db.delete(db_account)
    db.commit()
    return True

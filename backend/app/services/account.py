from sqlalchemy.orm import Session, joinedload, aliased
from sqlalchemy import func, case
from typing import List, Optional
import logging
from uuid import UUID

from backend.app.models.account import Account
from backend.app.models.delivery_unit import DeliveryUnit
from backend.app.models.project import Project
from backend.app.models.revenue import RevenueMaster
from backend.app.schemas.account import AccountCreate, AccountUpdate

logging.basicConfig(level=logging.DEBUG)


def get_accounts(db: Session, skip: int = 0, limit: Optional[int] = None) -> List[Account]:
    """    Retrieve a list of accounts with aggregated project and revenue metrics.    """
    # Project metrics subquery
    project_metrics = db.query(
        Project.account_id,
        func.count(Project.id).label("project_count"),
        func.sum(case((Project.status.ilike('active'), 1), else_=0)).label("active_project_count"),
        func.sum(case((Project.status.ilike('inactive'), 1), else_=0)).label("inactive_project_count"),
        func.sum(Project.ai_direct_hours + Project.ai_assist_hours).label("total_ai_hours")
    ).group_by(Project.account_id).subquery()

    # Revenue metrics subquery - aggregated by account through projects
    revenue_metrics = db.query(
        Project.account_id,
        func.sum(RevenueMaster.total_revenue).label("total_revenue"),
        func.sum(RevenueMaster.total_ai_revenue).label("ai_revenue")
    ).join(
        RevenueMaster, Project.id == RevenueMaster.project_id
    ).group_by(Project.account_id).subquery()

    project_metrics_alias = aliased(project_metrics, name="project_metrics")
    revenue_metrics_alias = aliased(revenue_metrics, name="revenue_metrics")

    accounts_query = db.query(
        Account,
        project_metrics_alias.c.project_count,
        project_metrics_alias.c.active_project_count,
        project_metrics_alias.c.inactive_project_count,
        project_metrics_alias.c.total_ai_hours,
        revenue_metrics_alias.c.total_revenue,
        revenue_metrics_alias.c.ai_revenue
    ).outerjoin(
        project_metrics_alias, Account.id == project_metrics_alias.c.account_id
    ).outerjoin(
        revenue_metrics_alias, Account.id == revenue_metrics_alias.c.account_id
    ).options(
        joinedload(Account.delivery_unit)
    ).order_by(
        case(
            (revenue_metrics_alias.c.total_revenue > 0, 1),
            else_=0
        ).desc(),
        revenue_metrics_alias.c.total_revenue.desc().nullslast(),
        Account.created_at.desc()
    )

    if limit is not None:
        accounts_query = accounts_query.limit(limit)
    
    results = accounts_query.offset(skip).all()

    accounts_with_metrics = []
    for account, project_count, active_count, inactive_count, ai_hours, total_rev, ai_rev in results:
        account.project_count = project_count or 0
        account.active_project_count = active_count or 0
        account.inactive_project_count = inactive_count or 0
        ai_hours_val = ai_hours or 0.0
        if isinstance(ai_hours_val, float) and (ai_hours_val != ai_hours_val):  
            ai_hours_val = 0.0
        account.total_ai_hours = ai_hours_val

        total_rev_val = float(total_rev) if total_rev else 0.0
        if total_rev_val != total_rev_val:  
            total_rev_val = 0.0
        account.total_revenue = total_rev_val
        
        ai_rev_val = float(ai_rev) if ai_rev else 0.0
        if ai_rev_val != ai_rev_val: 
            ai_rev_val = 0.0
        account.ai_revenue = ai_rev_val

        if account.total_revenue > 0:
            account.ai_penetration_pct = (account.ai_revenue / account.total_revenue * 100)
        else:
            account.ai_penetration_pct = 0.0
            
        accounts_with_metrics.append(account)

    return accounts_with_metrics


def get_account(db: Session, account_id: UUID) -> Optional[Account]:
    """    Retrieve a single account by ID with its projects and calculated metrics.    """
    # Project metrics subquery
    project_metrics = db.query(
        Project.account_id,
        func.count(Project.id).label("project_count"),
        func.sum(case((Project.status.ilike('active'), 1), else_=0)).label("active_project_count"),
        func.sum(case((Project.status.ilike('inactive'), 1), else_=0)).label("inactive_project_count"),
        func.sum(Project.ai_direct_hours + Project.ai_assist_hours).label("total_ai_hours")
    ).filter(Project.account_id == account_id).group_by(Project.account_id).subquery()

    # Revenue metrics subquery
    revenue_metrics = db.query(
        Project.account_id,
        func.sum(RevenueMaster.total_revenue).label("total_revenue"),
        func.sum(RevenueMaster.total_ai_revenue).label("ai_revenue")
    ).join(
        RevenueMaster, Project.id == RevenueMaster.project_id
    ).filter(
        Project.account_id == account_id
    ).group_by(Project.account_id).subquery()

    project_metrics_alias = aliased(project_metrics, name="project_metrics")
    revenue_metrics_alias = aliased(revenue_metrics, name="revenue_metrics")

    result = db.query(
        Account,
        project_metrics_alias.c.project_count,
        project_metrics_alias.c.active_project_count,
        project_metrics_alias.c.inactive_project_count,
        project_metrics_alias.c.total_ai_hours,
        revenue_metrics_alias.c.total_revenue,
        revenue_metrics_alias.c.ai_revenue
    ).outerjoin(
        project_metrics_alias, Account.id == project_metrics_alias.c.account_id
    ).outerjoin(
        revenue_metrics_alias, Account.id == revenue_metrics_alias.c.account_id
    ).options(
        joinedload(Account.delivery_unit),
        joinedload(Account.projects)
    ).filter(Account.id == account_id).first()

    if not result:
        return None

    account, project_count, active_count, inactive_count, ai_hours, total_rev, ai_rev = result

    account.project_count = project_count or 0
    account.active_project_count = active_count or 0
    account.inactive_project_count = inactive_count or 0

    ai_hours_val = ai_hours or 0.0
    if isinstance(ai_hours_val, float) and (ai_hours_val != ai_hours_val):  
        ai_hours_val = 0.0
    account.total_ai_hours = ai_hours_val

    total_rev_val = float(total_rev) if total_rev else 0.0
    if total_rev_val != total_rev_val: 
        total_rev_val = 0.0
    account.total_revenue = total_rev_val
    
    ai_rev_val = float(ai_rev) if ai_rev else 0.0
    if ai_rev_val != ai_rev_val:  
        ai_rev_val = 0.0
    account.ai_revenue = ai_rev_val

    if account.total_revenue > 0:
        account.ai_penetration_pct = (account.ai_revenue / account.total_revenue * 100)
    else:
        account.ai_penetration_pct = 0.0
    
    return account


def create_account(db: Session, account_data: AccountCreate) -> Account:
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
    db_account = db.query(Account).filter(Account.id == account_id).first()
    if db_account:
        update_data = account_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_account, key, value)
        
        db.commit()
        db.refresh(db_account)
        return db_account
    return None


def delete_account(db: Session, account_id: UUID) -> bool:
    db_account = db.query(Account).filter(Account.id == account_id).first()
    if not db_account:
        return False
    projects = db.query(Project).filter(Project.account_id == account_id).all()
    
    # Delete revenues for all projects (will cascade if relationship is set up)
    for project in projects:
        db.query(RevenueMaster).filter(RevenueMaster.project_id == project.id).delete(synchronize_session=False)
    db.query(Project).filter(Project.account_id == account_id).delete(synchronize_session=False)

    db.delete(db_account)
    db.commit()
    return True
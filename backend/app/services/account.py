from sqlalchemy.orm import Session, joinedload, aliased
from sqlalchemy import func, case, text
from typing import List, Optional
import logging
from uuid import UUID

from backend.app.models.account import Account, AccountMetricsMV
from backend.app.models.delivery_unit import DeliveryUnit
from backend.app.models.project import Project
from backend.app.models.revenue import RevenueMaster
from backend.app.schemas.account import AccountCreate, AccountUpdate

logging.basicConfig(level=logging.DEBUG)


def get_accounts_2(db: Session, skip: int = 0, limit: Optional[int] = None) -> List[Account]:
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

def get_accounts(db: Session, skip: int = 0, limit: Optional[int] = None) -> List[Account]:
    """Retrieve accounts with pre-aggregated metrics from materialized view."""
    
    query = db.query(
        AccountMetricsMV,
        Account,
        DeliveryUnit
    ).join(
        Account, AccountMetricsMV.account_id == Account.id
    ).outerjoin(
        DeliveryUnit, AccountMetricsMV.delivery_unit_id == DeliveryUnit.id
    ).order_by(
        AccountMetricsMV.has_revenue.desc(),
        AccountMetricsMV.total_revenue.desc(),
        AccountMetricsMV.created_at.desc()
    )
    
    if limit is not None:
        query = query.limit(limit)
    
    results = query.offset(skip).all()
    
    accounts_with_metrics = []
    for mv_row, account, delivery_unit in results:
        account.delivery_unit = delivery_unit
        account.project_count = mv_row.project_count
        account.active_project_count = mv_row.active_project_count
        account.inactive_project_count = mv_row.inactive_project_count
        account.total_ai_hours = mv_row.total_ai_hours
        account.total_revenue = mv_row.total_revenue
        account.ai_revenue = mv_row.ai_revenue
        account.ai_penetration_pct = mv_row.ai_penetration_pct
        
        accounts_with_metrics.append(account)
    
    return accounts_with_metrics

def get_account(db: Session, account_id: UUID) -> Optional[Account]:
    result = db.query(
        Account,
        AccountMetricsMV
    ).outerjoin(
        AccountMetricsMV,
        Account.id == AccountMetricsMV.account_id
    ).options(
        joinedload(Account.delivery_unit),
        joinedload(Account.projects)
    ).filter(
        Account.id == account_id
    ).first()
    
    if not result:
        return None
    
    account, metrics = result

    if metrics:
        account.project_count = metrics.project_count
        account.active_project_count = metrics.active_project_count
        account.inactive_project_count = metrics.inactive_project_count
        account.total_ai_hours = metrics.total_ai_hours
        account.total_revenue = metrics.total_revenue
        account.ai_revenue = metrics.ai_revenue
        account.ai_penetration_pct = metrics.ai_penetration_pct
    else:
        account.project_count = 0
        account.active_project_count = 0
        account.inactive_project_count = 0
        account.total_ai_hours = 0.0
        account.total_revenue = 0.0
        account.ai_revenue = 0.0
        account.ai_penetration_pct = 0.0

        if account.projects:
            account.project_count = len(account.projects)
            account.active_project_count = sum(
                1 for p in account.projects if p.status and p.status.lower() == 'active'
            )
            account.inactive_project_count = sum(
                1 for p in account.projects if p.status and p.status.lower() == 'inactive'
            )
            account.total_ai_hours = sum(
                (p.ai_direct_hours or 0.0) + (p.ai_assist_hours or 0.0) 
                for p in account.projects
            )
    
    return account


def create_account(db: Session, account_data: AccountCreate) -> Account:
    """Create a new account and trigger materialized view refresh."""
    logging.debug(f"Creating account with data: {account_data}")
    try:
        db_account = Account(**account_data.model_dump())
        db.add(db_account)
        db.commit()
        db.refresh(db_account)

        try:
            db.execute(text("SELECT refresh_account_metrics_mv();"))
            db.commit()
        except Exception as e:
            logging.warning(f"Failed to refresh materialized view: {e}")

        db_account.project_count = 0
        db_account.active_project_count = 0
        db_account.inactive_project_count = 0
        db_account.total_ai_hours = 0.0
        db_account.total_revenue = 0.0
        db_account.ai_revenue = 0.0
        db_account.ai_penetration_pct = 0.0
        
        return db_account
    except Exception as e:
        logging.error(f"Error creating account: {e}")
        db.rollback()
        raise


def update_account(db: Session, account_id: UUID, account_data: AccountUpdate) -> Optional[Account]:
    """Update an account and trigger materialized view refresh."""
    db_account = db.query(Account).filter(Account.id == account_id).first()
    if db_account:
        update_data = account_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_account, key, value)
        
        db.commit()
        db.refresh(db_account)

        try:
            db.execute(text("SELECT refresh_account_metrics_mv();"))
            db.commit()
        except Exception as e:
            logging.warning(f"Failed to refresh materialized view: {e}")

        return get_account(db, account_id)
    
    return None


def delete_account(db: Session, account_id: UUID) -> bool:
    """Delete an account and all related data, then refresh materialized view."""
    db_account = db.query(Account).filter(Account.id == account_id).first()
    if not db_account:
        return False

    projects = db.query(Project).filter(Project.account_id == account_id).all()

    for project in projects:
        db.query(RevenueMaster).filter(
            RevenueMaster.project_id == project.id
        ).delete(synchronize_session=False)

    db.query(Project).filter(
        Project.account_id == account_id
    ).delete(synchronize_session=False)

    db.delete(db_account)
    db.commit()

    try:
        db.execute(text("SELECT refresh_account_metrics_mv();"))
        db.commit()
    except Exception as e:
        logging.warning(f"Failed to refresh materialized view after deletion: {e}")
    
    return True


def refresh_account_metrics(db: Session) -> dict:
    """
    Manually refresh the account metrics materialized view.
    Can be called from an admin endpoint or scheduled task.
    """
    try:
        db.execute(text("SELECT refresh_account_metrics_mv();"))
        db.commit()
        return {"status": "success", "message": "Account metrics refreshed successfully"}
    except Exception as e:
        db.rollback()
        logging.error(f"Error refreshing account metrics: {e}")
        return {"status": "error", "message": str(e)}


def get_accounts_with_filters(
    db: Session,
    skip: int = 0,
    limit: Optional[int] = None,
    delivery_unit_id: Optional[UUID] = None,
    min_revenue: Optional[float] = None,
    has_active_projects: Optional[bool] = None,
    search_name: Optional[str] = None
) -> List[Account]:
    """
    Retrieve accounts with various filters using materialized view.
    """
    query = db.query(
        Account,
        AccountMetricsMV
    ).join(
        AccountMetricsMV,
        Account.id == AccountMetricsMV.account_id
    ).options(
        joinedload(Account.delivery_unit)
    )
    
    # Apply filters
    if delivery_unit_id:
        query = query.filter(Account.delivery_unit_id == delivery_unit_id)
    
    if min_revenue is not None:
        query = query.filter(AccountMetricsMV.total_revenue >= min_revenue)
    
    if has_active_projects is not None:
        if has_active_projects:
            query = query.filter(AccountMetricsMV.active_project_count > 0)
        else:
            query = query.filter(AccountMetricsMV.active_project_count == 0)
    
    if search_name:
        query = query.filter(Account.name.ilike(f"%{search_name}%"))
    
    # Order by
    query = query.order_by(
        AccountMetricsMV.has_revenue.desc(),
        AccountMetricsMV.total_revenue.desc(),
        Account.created_at.desc()
    )
    
    if limit is not None:
        query = query.limit(limit)
    
    results = query.offset(skip).all()
    
    accounts_with_metrics = []
    for account, metrics in results:
        account.project_count = metrics.project_count
        account.active_project_count = metrics.active_project_count
        account.inactive_project_count = metrics.inactive_project_count
        account.total_ai_hours = metrics.total_ai_hours
        account.total_revenue = metrics.total_revenue
        account.ai_revenue = metrics.ai_revenue
        account.ai_penetration_pct = metrics.ai_penetration_pct
        
        accounts_with_metrics.append(account)
    
    return accounts_with_metrics


def get_account_count(db: Session, has_revenue: Optional[bool] = None) -> int:
    """Get total count of accounts, optionally filtered by revenue status."""
    query = db.query(func.count(AccountMetricsMV.account_id))
    
    if has_revenue is not None:
        if has_revenue:
            query = query.filter(AccountMetricsMV.has_revenue == 1)
        else:
            query = query.filter(AccountMetricsMV.has_revenue == 0)
    
    return query.scalar()


def get_top_revenue_accounts(db: Session, limit: int = 10) -> List[Account]:
    """Get top N accounts by revenue using materialized view."""
    query = db.query(
        Account,
        AccountMetricsMV
    ).join(
        AccountMetricsMV,
        Account.id == AccountMetricsMV.account_id
    ).options(
        joinedload(Account.delivery_unit)
    ).filter(
        AccountMetricsMV.total_revenue > 0
    ).order_by(
        AccountMetricsMV.total_revenue.desc()
    ).limit(limit)
    
    results = query.all()
    
    accounts_with_metrics = []
    for account, metrics in results:
        account.project_count = metrics.project_count
        account.active_project_count = metrics.active_project_count
        account.inactive_project_count = metrics.inactive_project_count
        account.total_ai_hours = metrics.total_ai_hours
        account.total_revenue = metrics.total_revenue
        account.ai_revenue = metrics.ai_revenue
        account.ai_penetration_pct = metrics.ai_penetration_pct
        
        accounts_with_metrics.append(account)
    
    return accounts_with_metrics
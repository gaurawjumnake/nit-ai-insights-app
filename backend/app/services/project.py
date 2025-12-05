from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID
from uuid import UUID as _UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, and_, extract

from backend.app.models.project import Project
from backend.app.models.account import Account
from backend.app.models.revenue import RevenueMaster
from backend.app.models.delivery_unit import DeliveryUnit
from backend.app.schemas.project import ProjectCreate, ProjectUpdate, ProjectSummary


def get_projects_2(db: Session, skip: int = 0, limit: int = 100) -> List[Project]:
    """Retrieve a list of all projects."""
    return db.query(Project).options(joinedload(Project.account)).all()


def get_project_2(db: Session, project_id: UUID) -> Optional[Project]:
    """Retrieve a single project by ID."""
    return db.query(Project).options(joinedload(Project.account)).filter(Project.id == project_id).first()


def get_projects_by_account_2(db: Session, account_id: UUID) -> List[Project]:
    """Retrieve all projects for a specific account."""
    return db.query(Project).filter(Project.account_id == account_id).all()


def get_project_by_name_and_account_id(db: Session, project_name: str, account_id: UUID) -> Optional[Project]:
    """Retrieve a single project by name and account ID."""
    return db.query(Project).filter(
        Project.name == project_name, 
        Project.account_id == account_id
    ).first()


def _sanitize_project_payload(project_dict: dict) -> dict:
    """Coerce incoming payload to the correct types that match the DB schema."""
    from datetime import datetime

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

    # Convert integer fields
    if "ai_direct_people" in project_dict and project_dict["ai_direct_people"] is not None:
        try:
            project_dict["ai_direct_people"] = int(project_dict["ai_direct_people"])
        except Exception:
            project_dict["ai_direct_people"] = 0

    # Convert float fields
    for key in [
        "ai_direct_hours",
        "ai_assist_hours",
        "code_coverage_pct",
    ]:
        if key in project_dict and project_dict[key] is not None:
            try:
                project_dict[key] = float(project_dict[key])
            except Exception:
                project_dict[key] = 0.0

    # Parse dates
    for key in [
        "from_date",
        "to_date",
        "proposal_end_date",
        "expected_win_date",
    ]:
        if key in project_dict:
            project_dict[key] = parse_dt(project_dict[key])

    # Handle tech_stack
    tech_stack = project_dict.get("tech_stack")
    if tech_stack in ("", None):
        project_dict["tech_stack"] = None
    elif isinstance(tech_stack, str):
        project_dict["tech_stack"] = [s.strip() for s in tech_stack.split(",") if s.strip()]

    # Convert account_id to UUID
    acc_id = project_dict.get("account_id")
    if acc_id is not None:
        try:
            project_dict["account_id"] = _UUID(str(acc_id))
        except Exception:
            pass

    return project_dict


def create_project(db: Session, project_data: ProjectCreate) -> Project:
    """Create a new project."""
    project_dict = project_data.model_dump(exclude_unset=True)
    project_dict = _sanitize_project_payload(project_dict)
    
    # Remove project_type if None
    if project_dict.get("project_type") is None:
        project_dict.pop("project_type", None)
    
    db_project = Project(**project_dict)
    db.add(db_project)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Invalid project payload: ensure account_id exists and types are valid") from e
    db.refresh(db_project)
    return db_project


def update_project(db: Session, project_id: UUID, project_data: ProjectUpdate) -> Optional[Project]:
    """Update an existing project by ID."""
    db_project = get_project_2(db, project_id)
    if db_project:
        update_data = project_data.model_dump(exclude_unset=True)
        update_data = _sanitize_project_payload(update_data)
        
        for key, value in update_data.items():
            setattr(db_project, key, value)
        
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise ValueError("Invalid update: foreign key or data type issue") from e
        db.refresh(db_project)
        return db_project
    return None


def delete_project(db: Session, project_id: UUID) -> bool:
    """Delete a project by ID."""
    db_project = get_project_2(db, project_id)
    if db_project:
        db.delete(db_project)
        db.commit()
        return True
    return False

def get_projects(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    account_id: Optional[UUID] = None,
    project_status: Optional[str] = None,
    project_type: Optional[str] = None,
    delivery_unit_id: Optional[UUID] = None
) -> List[ProjectSummary]:
    query = db.query(
        Project.id.label("project_id"),
        Project.name.label("project_name"),
        Project.account_id,
        Project.status.label("project_status"),
        Project.project_type,
        Project.from_date,
        Project.to_date,
        Project.ai_direct_hours,
        Project.ai_assist_hours,
        Account.name.label("account_name"),
        DeliveryUnit.name.label("delivery_unit_name"),

        func.coalesce(func.sum(RevenueMaster.expected_revenue), 0).label("total_expected_rev"),
        func.coalesce(func.sum(RevenueMaster.ytd_revenue), 0).label("total_ytd_rev"),
        func.coalesce(func.sum(RevenueMaster.ai_direct_revenue), 0).label("total_ai_rev"),
        func.coalesce(func.sum(RevenueMaster.ai_assisted_revenue), 0).label("total_ai_assist_rev"),
        func.coalesce(func.sum(RevenueMaster.total_revenue), 0).label("total_revenue"),
        func.coalesce(func.max(RevenueMaster.ai_direct_people), 0).label("ai_direct_people"),
        func.extract('month', Project.from_date).label("month"),
        func.extract('year', Project.from_date).label("year")
    ).outerjoin(
        Account, Project.account_id == Account.id
    ).outerjoin(
        DeliveryUnit, Account.delivery_unit_id == DeliveryUnit.id
    ).outerjoin(
        RevenueMaster, Project.id == RevenueMaster.project_id
    )

    if account_id:
        query = query.filter(Project.account_id == account_id)
    
    if project_status:
        query = query.filter(Project.status.ilike(project_status))
    
    if project_type:
        query = query.filter(Project.project_type == project_type)
    
    if delivery_unit_id:
        query = query.filter(Account.delivery_unit_id == delivery_unit_id)

    query = query.group_by(
        Project.id,
        Project.name,
        Project.account_id,
        Project.status,
        Project.project_type,
        Project.from_date,
        Project.to_date,
        Project.ai_direct_hours,
        Project.ai_assist_hours,
        Account.name,
        DeliveryUnit.name
    ).order_by(
        Project.created_at.desc()
    )

    results = query.all() # offset(skip).limit(limit)

    project_summaries = []
    for row in results:
        summary = ProjectSummary(
            project_id=row.project_id,
            project_name=row.project_name,
            account_id=row.account_id,
            account_name=row.account_name or "",
            delivery_unit_name=row.delivery_unit_name or "",
            total_ai_direct_hours=float(row.ai_direct_hours or 0.0),
            total_ai_assist_hours=float(row.ai_assist_hours or 0.0),
            ai_direct_people=int(row.ai_direct_people or 0),
            project_status=row.project_status or "active",
            project_type=row.project_type or "",
            from_date=row.from_date,
            to_date=row.to_date,
            total_expected_rev=float(row.total_expected_rev),
            total_ytd_rev=float(row.total_ytd_rev),
            total_ai_rev=float(row.total_ai_rev),
            total_ai_assist_rev=float(row.total_ai_assist_rev),
            total_revenue=float(row.total_revenue),
            total_project_count=1,
            month=int(row.month) if row.month else None,
            year=int(row.year) if row.year else None,
        )
        project_summaries.append(summary)
    
    return project_summaries


def get_project(db: Session, project_id: UUID) -> Optional[Project]:
    """Retrieve a single project by ID with account relationship and revenue data."""
    project = get_project_2(db, project_id)
    if not project:
        return None
    
    revenue_data = db.query(
        func.coalesce(func.sum(RevenueMaster.expected_revenue), 0).label("expected_revenue"),
        func.coalesce(func.sum(RevenueMaster.ytd_revenue), 0).label("ytd_revenue"),
        func.coalesce(func.sum(RevenueMaster.ai_direct_revenue), 0).label("ai_revenue"),
        func.coalesce(func.sum(RevenueMaster.ai_assisted_revenue), 0).label("ai_assisted_revenue"),
        func.coalesce(func.sum(RevenueMaster.total_revenue), 0).label("total_revenue"),
    ).filter(
        RevenueMaster.project_id == project_id
    ).first()
    
    if revenue_data:
        project.expected_revenue = float(revenue_data.expected_revenue or 0)
        project.ytd_revenue = float(revenue_data.ytd_revenue or 0)
        project.ai_revenue = float(revenue_data.ai_revenue or 0)
        project.ai_assisted_revenue = float(revenue_data.ai_assisted_revenue or 0)
        project.total_revenue = float(revenue_data.total_revenue or 0)
        project.total_ai_revenue = project.ai_revenue + project.ai_assisted_revenue
    else:
        project.expected_revenue = 0.0
        project.ytd_revenue = 0.0
        project.ai_revenue = 0.0
        project.ai_assisted_revenue = 0.0
        project.total_revenue = 0.0
        project.total_ai_revenue = 0.0
    
    return project


def get_projects_by_account(
    db: Session, 
    account_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> List[ProjectSummary]:
    return get_projects(
        db=db,
        skip=skip,
        limit=limit,
        account_id=account_id
    )


def get_projects_count(
    db: Session,
    account_id: Optional[UUID] = None,
    project_status: Optional[str] = None
) -> int:

    query = db.query(func.count(Project.id))
    
    if account_id:
        query = query.filter(Project.account_id == account_id)
    
    if project_status:
        query = query.filter(Project.status.ilike(project_status))
    
    return query.scalar()


def get_projects_with_high_ai_penetration(
    db: Session,
    min_penetration: float = 50.0,
    limit: int = 10
) -> List[ProjectSummary]:
    """
    Get projects with high AI penetration percentage.
    """
    subquery = db.query(
        Project.id.label("project_id"),
        func.coalesce(func.sum(RevenueMaster.total_revenue), 0).label("total_revenue"),
        func.coalesce(
            func.sum(RevenueMaster.ai_direct_revenue) + func.sum(RevenueMaster.ai_assisted_revenue),
            0
        ).label("total_ai_revenue")
    ).outerjoin(
        RevenueMaster, Project.id == RevenueMaster.project_id
    ).group_by(
        Project.id
    ).subquery()
    
    # Main query
    query = db.query(
        Project.id.label("project_id"),
        Project.name.label("project_name"),
        Project.account_id,
        Project.status.label("project_status"),
        Project.project_type,
        Project.from_date,
        Project.to_date,
        Project.ai_direct_hours,
        Project.ai_assist_hours,
        Account.name.label("account_name"),
        DeliveryUnit.name.label("delivery_unit_name"),
        func.coalesce(func.sum(RevenueMaster.expected_revenue), 0).label("total_expected_rev"),
        func.coalesce(func.sum(RevenueMaster.ytd_revenue), 0).label("total_ytd_rev"),
        func.coalesce(func.sum(RevenueMaster.ai_direct_revenue), 0).label("total_ai_rev"),
        func.coalesce(func.sum(RevenueMaster.ai_assisted_revenue), 0).label("total_ai_assist_rev"),
        func.coalesce(func.sum(RevenueMaster.total_revenue), 0).label("total_revenue"),
        func.coalesce(func.max(RevenueMaster.ai_direct_people), 0).label("ai_direct_people"),
        func.extract('month', Project.from_date).label("month"),
        func.extract('year', Project.from_date).label("year")
    ).join(
        subquery, Project.id == subquery.c.project_id
    ).outerjoin(
        Account, Project.account_id == Account.id
    ).outerjoin(
        DeliveryUnit, Account.delivery_unit_id == DeliveryUnit.id
    ).outerjoin(
        RevenueMaster, Project.id == RevenueMaster.project_id
    ).filter(
        subquery.c.total_revenue > 0,
        (subquery.c.total_ai_revenue / subquery.c.total_revenue * 100) >= min_penetration
    ).group_by(
        Project.id,
        Project.name,
        Project.account_id,
        Project.status,
        Project.project_type,
        Project.from_date,
        Project.to_date,
        Project.ai_direct_hours,
        Project.ai_assist_hours,
        Account.name,
        DeliveryUnit.name
    ).order_by(
        (subquery.c.total_ai_revenue / subquery.c.total_revenue).desc()
    ).limit(limit)
    
    results = query.all()
    
    project_summaries = []
    for row in results:
        summary = ProjectSummary(
            project_id=row.project_id,
            project_name=row.project_name,
            account_id=row.account_id,
            account_name=row.account_name or "",
            delivery_unit_name=row.delivery_unit_name or "",
            total_ai_direct_hours=float(row.ai_direct_hours or 0.0),
            total_ai_assist_hours=float(row.ai_assist_hours or 0.0),
            ai_direct_people=int(row.ai_direct_people or 0),
            project_status=row.project_status or "active",
            project_type=row.project_type or "",
            from_date=row.from_date,
            to_date=row.to_date,
            total_expected_rev=float(row.total_expected_rev),
            total_ytd_rev=float(row.total_ytd_rev),
            total_ai_rev=float(row.total_ai_rev),
            total_ai_assist_rev=float(row.total_ai_assist_rev),
            total_revenue=float(row.total_revenue),
            total_project_count=1,
            month=int(row.month) if row.month else None,
            year=int(row.year) if row.year else None,
        )
        project_summaries.append(summary)
    
    return project_summaries


def get_top_revenue_projects(
    db: Session,
    limit: int = 10,
    project_status: Optional[str] = "active"
) -> List[ProjectSummary]:
    """
    Get top N projects by total revenue.
    """
    query = db.query(
        Project.id.label("project_id"),
        Project.name.label("project_name"),
        Project.account_id,
        Project.status.label("project_status"),
        Project.project_type,
        Project.from_date,
        Project.to_date,
        Project.ai_direct_hours,
        Project.ai_assist_hours,
        Account.name.label("account_name"),
        DeliveryUnit.name.label("delivery_unit_name"),
        func.coalesce(func.sum(RevenueMaster.expected_revenue), 0).label("total_expected_rev"),
        func.coalesce(func.sum(RevenueMaster.ytd_revenue), 0).label("total_ytd_rev"),
        func.coalesce(func.sum(RevenueMaster.ai_direct_revenue), 0).label("total_ai_rev"),
        func.coalesce(func.sum(RevenueMaster.ai_assisted_revenue), 0).label("total_ai_assist_rev"),
        func.coalesce(func.sum(RevenueMaster.total_revenue), 0).label("total_revenue"),
        func.coalesce(func.max(RevenueMaster.ai_direct_people), 0).label("ai_direct_people"),
        func.extract('month', Project.from_date).label("month"),
        func.extract('year', Project.from_date).label("year")
    ).outerjoin(
        Account, Project.account_id == Account.id
    ).outerjoin(
        DeliveryUnit, Account.delivery_unit_id == DeliveryUnit.id
    ).outerjoin(
        RevenueMaster, Project.id == RevenueMaster.project_id
    )
    
    if project_status:
        query = query.filter(Project.status.ilike(project_status))
    
    query = query.group_by(
        Project.id,
        Project.name,
        Project.account_id,
        Project.status,
        Project.project_type,
        Project.from_date,
        Project.to_date,
        Project.ai_direct_hours,
        Project.ai_assist_hours,
        Account.name,
        DeliveryUnit.name
    ).having(
        func.sum(RevenueMaster.total_revenue) > 0
    ).order_by(
        func.sum(RevenueMaster.total_revenue).desc()
    ).limit(limit)
    
    results = query.all()
    
    project_summaries = []
    for row in results:
        summary = ProjectSummary(
            project_id=row.project_id,
            project_name=row.project_name,
            account_id=row.account_id,
            account_name=row.account_name or "",
            delivery_unit_name=row.delivery_unit_name or "",
            total_ai_direct_hours=float(row.ai_direct_hours or 0.0),
            total_ai_assist_hours=float(row.ai_assist_hours or 0.0),
            ai_direct_people=int(row.ai_direct_people or 0),
            project_status=row.project_status or "active",
            project_type=row.project_type or "",
            from_date=row.from_date,
            to_date=row.to_date,
            total_expected_rev=float(row.total_expected_rev),
            total_ytd_rev=float(row.total_ytd_rev),
            total_ai_rev=float(row.total_ai_rev),
            total_ai_assist_rev=float(row.total_ai_assist_rev),
            total_revenue=float(row.total_revenue),
            total_project_count=1,
            month=int(row.month) if row.month else None,
            year=int(row.year) if row.year else None,
        )
        project_summaries.append(summary)
    
    return project_summaries



# Test Scripts to check connection ---------------------------------------------------------------------------------------------------

# from backend.app.db.session import SessionLocal

# def test_get_projects():
#     db = SessionLocal()
#     try:
#         projects = get_projects(db)
#         print(f"Found {len(projects)} projects")
#         for proj in projects:
#             print(f"  - {proj.name} (ID: {proj.id})")
#     except Exception as e:
#         print(f"Error: {e}")
#     finally:
#         db.close()

# if __name__ == "__main__":
#     test_get_projects()

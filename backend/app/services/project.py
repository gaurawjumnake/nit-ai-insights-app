from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID

from ..models.project import Project
from sqlalchemy.exc import IntegrityError
from uuid import UUID as _UUID
from ..models.account import Account
from ..schemas.project import ProjectCreate, ProjectUpdate


def get_projects(db: Session, skip: int = 0, limit: int = 100) -> List[Project]:
    """Retrieve a list of all projects."""
    return db.query(Project).options(joinedload(Project.account)).offset(skip).limit(limit).all()


def get_project(db: Session, project_id: str) -> Optional[Project]:
    """Retrieve a single project by ID."""
    return db.query(Project).options(joinedload(Project.account)).filter(Project.id == project_id).first()


def get_projects_by_account(db: Session, account_id: UUID) -> List[Project]:
    """Retrieve all projects for a specific account."""
    return db.query(Project).filter(Project.account_id == str(account_id)).all()


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

    for key in [
        "expected_revenue",
        "ytd_revenue",
        "ai_revenue",
        "ai_assisted_revenue",
        "total_ai_revenue",
        "ai_direct_people",
        "ai_assisted_people",
        "ai_direct_hours",
        "ai_assist_hours",
        "code_coverage_pct",
    ]:
        if key in project_dict and project_dict[key] is not None:
            try:
                project_dict[key] = float(project_dict[key])
            except Exception:
                project_dict[key] = 0.0

    for key in [
        "from_date",
        "to_date",
        "proposal_end_date",
        "expected_win_date",
    ]:
        if key in project_dict:
            project_dict[key] = parse_dt(project_dict[key])

    tech_stack = project_dict.get("tech_stack")
    if tech_stack in ("", None):
        project_dict["tech_stack"] = None
    elif isinstance(tech_stack, str):
        project_dict["tech_stack"] = [s.strip() for s in tech_stack.split(",") if s.strip()]

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
    if 'total_ai_revenue' not in project_dict or project_dict['total_ai_revenue'] == 0:
        ai_direct = project_dict.get('ai_revenue', 0) or 0
        ai_assisted = project_dict.get('ai_assisted_revenue', 0) or 0
        project_dict['total_ai_revenue'] = ai_direct + ai_assisted
    
    db_project = Project(**project_dict)
    db.add(db_project)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Invalid project payload: ensure account_id exists and types are valid") from e
    db.refresh(db_project)
    return db_project


def update_project(db: Session, project_id: str, project_data: ProjectUpdate) -> Optional[Project]:
    """Update an existing project by ID."""
    db_project = get_project(db, project_id)
    if db_project:
        update_data = project_data.model_dump(exclude_unset=True)
        
        if 'ai_revenue' in update_data or 'ai_assisted_revenue' in update_data:
            ai_direct = update_data.get('ai_revenue', db_project.ai_revenue) or 0
            ai_assisted = update_data.get('ai_assisted_revenue', db_project.ai_assisted_revenue) or 0
            update_data['total_ai_revenue'] = ai_direct + ai_assisted
        
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


def delete_project(db: Session, project_id: str) -> bool:
    """Delete a project by ID."""
    db_project = get_project(db, project_id)
    if db_project:
        db.delete(db_project)
        db.commit()
        return True
    return False


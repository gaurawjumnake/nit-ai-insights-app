from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID
from uuid import UUID as _UUID
from sqlalchemy.exc import IntegrityError

from backend.app.models.project import Project
from backend.app.models.account import Account
from backend.app.schemas.project import ProjectCreate, ProjectUpdate


def get_projects(db: Session, skip: int = 0, limit: int = 100) -> List[Project]:
    """Retrieve a list of all projects."""
    return db.query(Project).options(joinedload(Project.account)).all()


def get_project(db: Session, project_id: UUID) -> Optional[Project]:
    """Retrieve a single project by ID."""
    return db.query(Project).options(joinedload(Project.account)).filter(Project.id == project_id).first()


def get_projects_by_account(db: Session, account_id: UUID) -> List[Project]:
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
    db_project = get_project(db, project_id)
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
    db_project = get_project(db, project_id)
    if db_project:
        db.delete(db_project)
        db.commit()
        return True
    return False

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

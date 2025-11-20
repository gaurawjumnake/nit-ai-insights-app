from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from backend.app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut
from backend.app.services import project as project_service
from backend.app.db.session import get_db

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


@router.get("/", response_model=List[ProjectOut])
def read_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Retrieve a list of all projects."""
    projects = project_service.get_projects(db, skip=skip, limit=limit)
    return projects


@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db)
):
    """Create a new project."""
    try:
        db_project = project_service.create_project(db=db, project_data=project)
        return db_project
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not create project: {str(e)}"
        )


# Keep static route before dynamic route for robustness
@router.get("/account/{account_id}", response_model=List[ProjectOut])
def read_projects_by_account(
    account_id: UUID,
    db: Session = Depends(get_db)
):
    """Retrieve all projects for a specific account."""
    projects = project_service.get_projects_by_account(db, account_id=account_id)
    return projects


@router.get("/{project_id}", response_model=ProjectOut)
def read_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Retrieve details for a single project by ID."""
    try:
        db_project = project_service.get_project(db, project_id=project_id)
        if db_project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return db_project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to fetch project: {str(e)}")


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str,
    project: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing project's details."""
    try:
        db_project = project_service.update_project(db, project_id=project_id, project_data=project)
        if db_project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return db_project
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to update project: {str(e)}")


@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Delete a specific project."""
    success = project_service.delete_project(db, project_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return {"message": "Project deleted successfully"}




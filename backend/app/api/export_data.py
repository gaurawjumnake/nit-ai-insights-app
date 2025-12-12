from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.app.schemas.project import ProjectSummary,ProjectBase,ProjectOut,ProjectExport
from backend.app.schemas.revenue import RevenueSummary,RevenueBase,RevenueOut,RevenueExport
from backend.app.services import export_services
from backend.app.db.session import get_db

router = APIRouter(
    prefix="/export_data",
    tags=["export_data"]
)

@router.get("/all_projects", response_model=List[ProjectExport])
def export_all_projects(
    db: Session = Depends(get_db)
):
    """
    Export all projects.
    """
    projects = export_services.get_projects(db)
    return projects

@router.get("/all_revenues", response_model=List[RevenueExport])
def export_all_revenues(
    db: Session = Depends(get_db)
):
    """
    Export all revenues.
    """
    revenues = export_services.get_revenues(db)
    return revenues

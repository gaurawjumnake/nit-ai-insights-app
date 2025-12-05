from fastapi import APIRouter, UploadFile, File, Depends, HTTPException,status
from sqlalchemy.orm import Session
from typing import Optional, List
from sqlalchemy import func, and_, Table, MetaData
from backend.app.db.session import get_db
from backend.app.services.dashboard_services import MasterSummary
from backend.app.schemas.dashboard import DashboardStatsOut
from backend.app.schemas.project import ProjectSummary

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
)

@router.post("/")
async def refresh_rev_master(db: Session = Depends(get_db)):
    pass

@router.get("/get_data", response_model=List[ProjectSummary])
async def get_data(db: Session = Depends(get_db) ,
        account_name: Optional[str] = None,
        project_name: Optional[str] = None,
        project_status: Optional[str] = None,
        project_type: Optional[str] = None,
        month: Optional[int] = None,
        year: Optional[int] = None
    ):
    summary = MasterSummary()
    try:
        response = summary.get_project_level_summary(db,
                                                    account_name,
                                                    project_name,
                                                    project_status,
                                                    project_type,
                                                    month,
                                                    year)
        return response
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to update project: {str(e)}")





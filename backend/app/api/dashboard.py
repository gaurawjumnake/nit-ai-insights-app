from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from backend.app.db.session import get_db
from backend.app.services.dashboard_services import MasterSummary
from backend.app.services.account import get_account_revenue_summary
from backend.app.schemas.project import ProjectSummary
from backend.app.schemas.account import AccountRevenueSummary

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
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        delivery_unit_name: Optional[str] = None
    ):
    summary = MasterSummary()
    try:
        response = await summary.get_project_level_summary(db,
                                                    account_name,
                                                    project_name,
                                                    project_status,
                                                    project_type,
                                                    start_date,
                                                    end_date,
                                                    delivery_unit_name)
        return response
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to update project: {str(e)}")


@router.get("/account_summary", response_model=List[AccountRevenueSummary])
def get_account_revenue_summary_endpoint(
    db: Session = Depends(get_db),
    project_name: Optional[str] = None, 
    account_name: Optional[str] = None, 
    project_status: Optional[str] = None ,
    project_type: Optional[str] = None,
    month: Optional[int] = None, 
    year: Optional[int] = None, 
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    delivery_unit_name: Optional[str] = None, 
    limit: Optional[int] = None, 
    skip: int = 0
):
    """
    Get account-level revenue summary with all filters applied.
    Returns all accounts (or limited) with aggregated revenue data.
    """
    return get_account_revenue_summary(
        db=db,
        project_name = project_name,
        account_name = account_name,
        project_status=project_status,
        project_type=project_type,
        month=month,
        year=year,
        start_date=start_date,
        end_date=end_date,
        delivery_unit_name=delivery_unit_name,
        limit=limit,
        skip=skip
    )
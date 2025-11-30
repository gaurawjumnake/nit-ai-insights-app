from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.db.session import get_db
from backend.app.services.import_service import ImportProjectData, ImportRevenueData

router = APIRouter(
    prefix="/import",
    tags=["Import"],
)

@router.post("/project")
async def import_project(
    file: UploadFile = File(...),
    dry_run: Optional[bool] = False,
    db: Session = Depends(get_db),
):
    pmodata = ImportProjectData()
    if file.content_type not in [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "text/csv",
        "application/csv",
    ]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload .xlsx or .csv")

    try:
        contents = await file.read()
        summary = pmodata.import_projects_from_file(db, contents, filename=file.filename, dry_run=dry_run) # type:ignore
        return summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to import: {str(e)}")


@router.post("/revenue")
async def import_revenue(
    file: UploadFile = File(...),
    dry_run: Optional[bool] = False,
    db: Session = Depends(get_db),
):
    pmodata = ImportRevenueData()
    if file.content_type not in [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "text/csv",
        "application/csv",
    ]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload .xlsx or .csv")

    try:
        contents = await file.read()
        summary = pmodata.import_revenue_from_file(db, contents, filename=file.filename, dry_run=dry_run) # type:ignore
        return summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to import: {str(e)}")
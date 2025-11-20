from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.db.session import get_db
from backend.app.services.import_service import ImportAccountsData


router = APIRouter(
    prefix="/import",
    tags=["Import"],
)


@router.post("/excel")
async def import_excel(
    file: UploadFile = File(...),
    dry_run: Optional[bool] = False,
    db: Session = Depends(get_db),
):
    accounts = ImportAccountsData()
    if file.content_type not in [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "text/csv",
        "application/csv",
    ]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload .xlsx or .csv")

    try:
        contents = await file.read()
        summary = accounts.import_accounts_and_projects_from_file(db, contents, filename=file.filename, dry_run=dry_run) # type:ignore
        return summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to import: {str(e)}")



from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import os
from typing import Callable, Any
from backend.utitlites.doc_importer import import_and_save_file
from backend.app.db.session import get_db
from backend.app.services.import_service import ImportProjectData, ImportRevenueData
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
load_dotenv()

TEMP_DIR = Path(os.getenv("TEMP_DIR")) #type:ignore
PROJECT_SUCCESS_DIR = Path(os.getenv("PROJECT_SUCCESS_DIR")) #type:ignore
PROJECT_FAILED_DIR = Path(os.getenv("PROJECT_FAILED_DIR")) #type:ignore
REVENUE_SUCCESS_DIR = Path(os.getenv("REVENUE_SUCCESS_DIR")) #type:ignore
REVENUE_FAILED_DIR = Path(os.getenv("REVENUE_FAILED_DIR")) #type:ignore

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
    return await import_and_save_file(
        file=file,
        temp_dir=TEMP_DIR,
        success_dir=PROJECT_SUCCESS_DIR,
        failed_dir=PROJECT_FAILED_DIR,
        import_function=pmodata.import_projects_from_file,
        db=db,
        dry_run=dry_run # type:ignore
    )

@router.post("/revenue")
async def import_revenue(
    file: UploadFile = File(...),
    dry_run: Optional[bool] = False,
    db: Session = Depends(get_db),
):
    pmodata = ImportRevenueData()
    return await import_and_save_file(
        file=file,
        temp_dir=TEMP_DIR,
        success_dir=REVENUE_SUCCESS_DIR,
        failed_dir=REVENUE_FAILED_DIR,
        import_function=pmodata.import_revenue_from_file,
        db=db,
        dry_run=dry_run # type:ignore
    )


# @router.post("/project")
# async def import_project_old(
#     file: UploadFile = File(...),
#     dry_run: Optional[bool] = False,
#     db: Session = Depends(get_db),
# ):
#     if file.content_type not in [
#         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         "application/vnd.ms-excel",
#         "text/csv",
#         "application/csv",
#     ]:
#         raise HTTPException(status_code=400, detail="Unsupported file type. Upload .xlsx or .csv")

#     try:
#         contents = await file.read()

#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         safe_filename = f"{timestamp}_{file.filename}"
#         temp_file_path = TEMP_DIR / safe_filename
        
#         with open(temp_file_path, "wb") as buffer:
#             buffer.write(contents)
#         print(f"✓ File saved to: {temp_file_path}")

#         pmodata = ImportProjectData()
#         summary = pmodata.import_projects_from_file(
#             db, 
#             contents, 
#             filename=file.filename, #type:ignore
#             dry_run=dry_run #type:ignore
#         )
#         has_errors = summary.get("errors") and len(summary["errors"]) > 0
#         if not has_errors and not dry_run:
#             shutil.move(str(temp_file_path), str(SUCCESS_DIR / safe_filename))

#         elif not dry_run:
#             shutil.move(str(temp_file_path), str(FAILED_DIR / safe_filename))
#         else:
#             temp_file_path.unlink()  
        
#         return summary
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Failed to import: {str(e)}")


# @router.post("/revenue")
# async def import_revenue_old(
#     file: UploadFile = File(...),
#     dry_run: Optional[bool] = False,
#     db: Session = Depends(get_db),
# ):
#     pmodata = ImportRevenueData()
#     if file.content_type not in [
#         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         "application/vnd.ms-excel",
#         "text/csv",
#         "application/csv",
#     ]:
#         raise HTTPException(status_code=400, detail="Unsupported file type. Upload .xlsx or .csv")

#     try:
#         contents = await file.read()
#         summary = pmodata.import_revenue_from_file(db, contents, filename=file.filename, dry_run=dry_run) # type:ignore
#         return summary
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Failed to import: {str(e)}")
    
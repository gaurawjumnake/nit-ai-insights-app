from fastapi import APIRouter, UploadFile, HTTPException, File, Depends
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import os
import pytz # Ensure you have this installed: pip install pytz
from sqlalchemy.orm import Session
from uuid import UUID
from backend.app.db.session import get_db
# Import the helper utility
from backend.utitlites.doc_importer import import_and_save_document
# Import the NEW service functions
from backend.doc_insighter.services.tech_review import process_tech_review_document, get_project_document
from backend.doc_insighter.tools.app_logger import Logger
from dotenv import load_dotenv

log = Logger()
load_dotenv()

# Robust Environment Variable Loading
temp_path_str = os.getenv("TEMP_DIR", "./temp_uploads")
proj_doc_str = os.getenv("PROJECT_DOCUMENT_DIR", "./project_docs")
proj_fail_str = os.getenv("PROJECT_FAILED_DIR", "./failed_docs")

TEMP_DIR = Path(temp_path_str)
PROJECT_DOCUMENT_DIR = Path(proj_doc_str)
PROJECT_FAILED_DIR = Path(proj_fail_str)

# Ensure directories exist
for path in [TEMP_DIR, PROJECT_DOCUMENT_DIR, PROJECT_FAILED_DIR]:
    path.mkdir(parents=True, exist_ok=True)

supported_extensions = os.getenv("SUPPORTED_DOC_TYPE_EXTENSIONS", ".pdf,.docx,.doc,.txt,.md")

router = APIRouter(prefix="/document", tags=["Project-Documents"])

# Response Model
class ImportResponse(BaseModel):
    errors: List[str] = []
    records_processed: int
    records_created: int
    uploaded_file: Optional[str] = None
    file_size_mb: Optional[float] = None
    import_status: str
    document_id: Optional[str] = None
    operation: Optional[str] = None
    message: Optional[str] = None

@router.post("/import_tech_review/{project_id}", response_model=ImportResponse)
async def import_tech_review_document(
    project_id: UUID,
    file: UploadFile = File(...),
    dry_run: bool = False,  
    db: Session = Depends(get_db)
):
    """
    Import a Technical Design/Architecture document (PDF, DOCX) for Tech Review.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    file_extension = Path(file.filename).suffix.lower()
    
    # Basic check against supported extensions
    if file_extension not in supported_extensions and file_extension not in ['.pdf', '.docx', '.doc', '.txt', '.md']: 
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file format '{file_extension}'."
        )

    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    try:
        # Calls the shared importer with the TECH REVIEW processor
        result = await import_and_save_document(
            file=file,
            project_id=project_id, # type:ignore
            temp_dir=TEMP_DIR,
            success_dir=PROJECT_DOCUMENT_DIR,
            failed_dir=PROJECT_FAILED_DIR,
            import_function=process_tech_review_document, # <--- Specific Function
            db=db,
            dry_run=dry_run,
            document_type="TECH_REVIEW"
        )
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        log.log_error(f"Unexpected error in import_tech_review_document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/tech_review/{project_id}", response_model=None)
async def get_tech_review_report(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Retrieve the Tech Review Report for a project.
    """
    document_type = "TECH_REVIEW"
    try:
        doc = get_project_document(db, project_id, document_type) # type:ignore
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No Tech Review report found for project {project_id}"
            )
        
        # --- Timezone Conversion (UTC to IST/Local) ---
        created_at_display = None
        if doc.created_at:
            utc_time = doc.created_at.replace(tzinfo=pytz.UTC) if doc.created_at.tzinfo is None else doc.created_at
            # Change 'Asia/Kolkata' to your desired timezone
            local_time = utc_time.astimezone(pytz.timezone('Asia/Kolkata'))
            created_at_display = local_time.isoformat()

        return {
            "document_id": str(doc.id),
            "project_id": str(doc.project_id),
            "content": doc.content,
            "document_type": doc.document_type,
            "created_at": created_at_display 
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log.log_error(f"Error retrieving Tech Review document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve document: {str(e)}"
        )

@router.delete("/tech_review/{project_id}", response_model=None)
async def delete_tech_review_report(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete the Tech Review Report for a project.
    """
    document_type = "TECH_REVIEW"
    try:
        doc = get_project_document(db, project_id, document_type) # type:ignore
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No Tech Review report found for project {project_id}"
            )
        
        db.delete(doc)
        db.commit()
        
        log.log_info(f"Tech Review report deleted for project {project_id}")
        
        return {
            "message": "Tech Review report deleted successfully",
            "document_id": str(doc.id),
            "project_id": str(project_id)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log.log_error(f"Error deleting Tech Review report: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )
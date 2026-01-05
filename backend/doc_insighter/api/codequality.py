from fastapi import APIRouter, UploadFile, HTTPException, File, Depends
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import os
from sqlalchemy.orm import Session
from uuid import UUID
from backend.app.db.session import get_db
# Import the helper utility
from backend.utitlites.doc_importer import import_and_save_document
# Import the NEW service functions
from backend.doc_insighter.services.codequality import process_code_quality_document, get_project_document
from backend.doc_insighter.tools.app_logger import Logger
from dotenv import load_dotenv

log = Logger()
load_dotenv()

# Ensure these match your environment variables
supported_extensions = os.getenv("SUPPORTED_DOC_TYPE_EXTENSIONS")
# Note: For code quality, you might want to ensure .py, .js, .txt etc are in your .env supported list

TEMP_DIR = Path(os.getenv("TEMP_DIR")) # type:ignore
PROJECT_DOCUMENT_DIR = Path(os.getenv("PROJECT_DOCUMENT_DIR")) # type:ignore
PROJECT_FAILED_DIR = Path(os.getenv("PROJECT_FAILED_DIR")) # type:ignore

# Ensure directories exist
for path in [TEMP_DIR, PROJECT_DOCUMENT_DIR, PROJECT_FAILED_DIR]:
    path.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/document", tags=["Project-Documents"])

# Reusing the response model pattern
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

@router.post("/import_code_quality/{project_id}", response_model=ImportResponse)
async def import_code_quality_document(
    project_id: UUID,
    file: UploadFile = File(...),
    dry_run: bool = False,  
    db: Session = Depends(get_db)
):
    """
    Import a code file or document to generate a Code Quality Report.
    
    - project_id: UUID of the project
    - file: Code file (Python, JS, TXT, etc)
    - dry_run: If True, generates report without saving to database
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    file_extension = Path(file.filename).suffix.lower()
    
    # Note: Ensure your SUPPORTED_DOC_TYPE_EXTENSIONS in .env includes code extensions like .py, .js
    if file_extension not in supported_extensions: # type:ignore
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file format '{file_extension}'. Supported formats: {supported_extensions}"
        )

    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    try:
        # Calls the shared importer but passes the CODE QUALITY specific processor
        result = await import_and_save_document(
            file=file,
            project_id=project_id, # type:ignore
            temp_dir=TEMP_DIR,
            success_dir=PROJECT_DOCUMENT_DIR,
            failed_dir=PROJECT_FAILED_DIR,
            import_function=process_code_quality_document, # <--- Key change here
            db=db,
            dry_run=dry_run,
            document_type="CODE_QUALITY"
        )
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        log.log_error(f"Unexpected error in import_code_quality_document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/code_quality/{project_id}", response_model=None)
async def get_code_quality_report(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Retrieve the Code Quality Report for a project.
    """
    document_type = "CODE_QUALITY"
    try:
        doc = get_project_document(db, project_id, document_type) # type:ignore
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No Code Quality report found for project {project_id}"
            )
        
        return {
            "document_id": str(doc.id),
            "project_id": str(doc.project_id),
            "content": doc.content,
            "document_type": doc.document_type,
            "created_at": doc.created_at.isoformat() if doc.created_at else None # type:ignore
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log.log_error(f"Error retrieving Code Quality document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve document: {str(e)}"
        )

@router.delete("/code_quality/{project_id}", response_model=None)
async def delete_code_quality_report(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete the Code Quality Report for a project.
    """
    document_type = "CODE_QUALITY"
    try:
        doc = get_project_document(db, project_id, document_type) # type:ignore
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No Code Quality report found for project {project_id}"
            )
        
        db.delete(doc)
        db.commit()
        
        log.log_info(f"Code Quality report deleted for project {project_id}")
        
        return {
            "message": "Code Quality report deleted successfully",
            "document_id": str(doc.id),
            "project_id": str(project_id)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log.log_error(f"Error deleting Code Quality report: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )
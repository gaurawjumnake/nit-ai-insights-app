from fastapi import APIRouter, UploadFile, HTTPException, File, Depends
from pydantic import BaseModel
from typing import Optional, Dict, List
from pathlib import Path
import os
from sqlalchemy.orm import Session
from uuid import UUID
from backend.app.db.session import get_db
from backend.doc_insighter.tools.app_logger import Logger
from backend.utitlites.doc_importer import import_and_save_document
from dotenv import load_dotenv
from backend.doc_insighter.services.code_quality import process_code_quality_document, get_project_document

log = Logger()
load_dotenv()

supported_extensions = os.getenv("SUPPORTED_DOC_TYPE_EXTENSIONS")

TEMP_DIR = Path(os.getenv("TEMP_DIR"))
PROJECT_DOCUMENT_DIR = Path(os.getenv("PROJECT_DOCUMENT_DIR"))
PROJECT_FAILED_DIR = Path(os.getenv("PROJECT_FAILED_DIR"))

for path in [TEMP_DIR, PROJECT_DOCUMENT_DIR, PROJECT_FAILED_DIR]:
    path.mkdir(parents=True, exist_ok=True)


router = APIRouter(prefix="/document", tags=["Project-Documents"])

class InputRequest(BaseModel):
    file_path: str

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
    Import Code Quality document/report for a project.
    
    - project_id: UUID of the project
    - file: Document file containing code or code analysis
    - dry_run: If True, validates file without saving to database
    
    Returns import summary with document ID and operation status.
    """
    if not file.filename:
        raise HTTPException(
            status_code=400, 
            detail="No filename provided"
        )

    file_extension = Path(file.filename).suffix.lower()
     
    if file_extension not in supported_extensions: # type:ignore
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file format '{file_extension}'. Supported formats: {supported_extensions}"
        )

    if not project_id:
        raise HTTPException(
            status_code=400, 
            detail="project_id is required"
        )

    try:
        # --- NEW LOGIC START ---
        # 1. Define the project-specific directory
        # e.g. /var/www/project_docs/123e4567-e89b...
        project_success_dir = PROJECT_DOCUMENT_DIR / str(project_id)
        
        # 2. Create the directory immediately
        # This ensures the folder exists before the importer tries to save the file
        project_success_dir.mkdir(parents=True, exist_ok=True)
        
        # (Optional) Do the same for failed directory if you want isolation there too
        project_failed_dir = PROJECT_FAILED_DIR / str(project_id)
        project_failed_dir.mkdir(parents=True, exist_ok=True)
        # --- NEW LOGIC END ---
        result = await import_and_save_document(
            file=file,
            project_id=project_id, # type:ignore
            temp_dir=TEMP_DIR,
            success_dir=project_success_dir,
            failed_dir=project_failed_dir,
            import_function=process_code_quality_document, # Uses the Code Quality service logic
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
async def get_code_quality_document(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Retrieve Code Quality document for a project.
    - project_id: UUID of the project
    """
    document_type = "code_quality"
    try:
        doc = get_project_document(db, project_id, document_type) # type:ignore
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No Code Quality document found for project {project_id}"
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
async def delete_code_quality_document(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete Code Quality document for a project.
    - project_id: UUID of the project
    Returns confirmation of deletion.
    """
    document_type = "code_quality"
    try:
        doc = get_project_document(db, project_id, document_type) # type:ignore
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No Code Quality document found for project {project_id}"
            )
        
        db.delete(doc)
        db.commit()
        
        log.log_info(f"Code Quality document deleted for project {project_id}")
        
        return {
            "message": "Code Quality document deleted successfully",
            "document_id": str(doc.id),
            "project_id": str(project_id)
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        db.rollback()
        log.log_error(f"Error deleting Code Quality document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )
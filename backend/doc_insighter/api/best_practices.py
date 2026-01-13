from fastapi import APIRouter, UploadFile, HTTPException, File, Depends
from pydantic import BaseModel
from typing import Optional, Dict, List
from pathlib import Path
import os
from sqlalchemy.orm import Session
from uuid import UUID
from backend.app.db.session import get_db
from backend.utitlites.doc_importer import import_and_save_document
from backend.doc_insighter.services.best_practices import process_best_practices_document, get_project_document
from backend.doc_insighter.tools.app_logger import Logger
log = Logger()
from dotenv import load_dotenv

load_dotenv()
supported_extensions = os.getenv("SUPPORTED_DOC_TYPE_EXTENSIONS")

TEMP_DIR = Path(os.getenv("TEMP_DIR"))
PROJECT_DOCUMENT_DIR = Path(os.getenv("PROJECT_DOCUMENT_DIR"))
PROJECT_FAILED_DIR = Path(os.getenv("PROJECT_FAILED_DIR"))

for path in [TEMP_DIR, PROJECT_DOCUMENT_DIR, PROJECT_FAILED_DIR]:
    path.mkdir(parents=True, exist_ok=True)


router = APIRouter(prefix="/document", tags=["Project-Documents"])

class InputRequest(BaseModel):
    file_path:str

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

@router.post("/import_best_practices/{project_id}", response_model=ImportResponse)
async def import_best_practices_document(
    project_id: UUID,
    file: UploadFile = File(...),
    dry_run: bool = False,  
    db: Session = Depends(get_db)
):
    """
    Import Best Practices document for a project.
    
    - project_id: UUID of the project
    - file: Document file (PDF, DOCX, DOC, TXT)
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
            import_function=process_best_practices_document,
            db=db,
            dry_run=dry_run,
            document_type="BEST_PRACTICES"
        )
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        log.log_error(f"Unexpected error in import_best_practices_document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/best_practices/{project_id}", response_model=None)
async def get_best_practices_document(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Retrieve Best Practices document for a project.
    - project_id: UUID of the project
    """
    document_type = "best_practices"
    try:
        doc = get_project_document(db, project_id, document_type) # type:ignore
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No Best Practices document found for project {project_id}"
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
        log.log_error(f"Error retrieving Best Practices document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve document: {str(e)}"
        )

@router.delete("/best_practices/{project_id}", response_model=None)
async def delete_best_practices_document(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete Best Practices document for a project.
    - project_id: UUID of the project
    Returns confirmation of deletion.
    """
    document_type = "best_practices"
    try:
        doc = get_project_document(db, project_id, document_type) # type:ignore
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No Best Practices document found for project {project_id}"
            )
        
        db.delete(doc)
        db.commit()
        
        log.log_info(f"Best Practices document deleted for project {project_id}")
        
        return {
            "message": "Best Practices document deleted successfully",
            "document_id": str(doc.id),
            "project_id": str(project_id)
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        db.rollback()
        log.log_error(f"Error deleting Best Practices document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )
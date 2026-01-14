from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from typing import List, Optional
import os
import re
from pathlib import Path
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Import the service we just created
from backend.doc_insighter.services.project_file_service import ProjectFileService
from backend.app.db.session import get_db
from backend.app.models.document import ProjectDocument
from fastapi.responses import FileResponse


router = APIRouter(prefix="/document", tags=["Project-Documents"])

# Response Model for clean documentation
class FileInfo(BaseModel):
    file_name: str
    display_name: str
    size: str
    upload_date_str: str

@router.get("/list/{project_id}/{category}", response_model=List[FileInfo])
def list_category_files(project_id: UUID, category: str):
    """
    Returns a list of files for a specific project and category.
    
    - **project_id**: UUID of the project
    - **category**: 'wsr', 'sow', 'codequality', 'bestpractices', 'techreview', etc.
    """
    valid_categories = {
        'wsr', 'sow', 
        'codequality', 'code_quality', 
        'bestpractices', 'best_practices', 
        'techreview', 'tech_review'
    }
    
    if category.lower() not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of {valid_categories}")

    files = ProjectFileService.get_project_files(str(project_id), category)
    
    return files

@router.delete("/delete/{project_id}/{filename}")
def delete_file(project_id: UUID, filename: str, db: Session = Depends(get_db)):
    """
    Delete a specific file from the project folder.
    If the file is the latest one (active in DB), also delete the DB record.
    """
    type_map = {
        "_WSR_": ("wsr", "WSR"),
        "_SOW_": ("sow", "SOW"),
        "_CODE_QUALITY_": ("code_quality", "CODE_QUALITY"),
        "_TECH_REVIEW_": ("tech_review", "TECH_REVIEW"),
        "_BEST_PRACTICES_": ("best_practices", "BEST_PRACTICES")
    }
    
    category = None
    db_doc_type = None

    for key, (cat, doc_type) in type_map.items():
        if key in filename:
            category = cat
            db_doc_type = doc_type
            break
            
    is_latest_file = False
    if category:
        try:
            current_files = ProjectFileService.get_project_files(str(project_id), category)
            if current_files and current_files[0]['file_name'] == filename:
                is_latest_file = True
        except Exception as e:
            print(f"Error checking file status: {e}")

    success = ProjectFileService.delete_project_file(str(project_id), filename)
    if not success:
        raise HTTPException(status_code=404, detail="File not found or could not be deleted")

    if is_latest_file and db_doc_type:
        try:
            db.query(ProjectDocument).filter(
                ProjectDocument.project_id == project_id,
                ProjectDocument.document_type == db_doc_type
            ).delete(synchronize_session=False)
            
            db.commit()
            print(f"✓ All DB records deleted for {db_doc_type} (project: {project_id})")
        except Exception as e:
            print(f"Error deleting DB record: {e}")
            db.rollback()

    return {"message": "File deleted successfully"}

@router.get("/download/{project_id}/{filename}")
def download_project_file(project_id: UUID, filename: str):
    """
    Download a specific file from the project folder.
    """
    project_dir = Path(os.getenv("PROJECT_DOCUMENT_DIR", "uploaded_docs/project_docs")) / str(project_id)
    file_path = project_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path, 
        filename=filename, 
        media_type='application/octet-stream',
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
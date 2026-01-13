from fastapi import APIRouter, HTTPException
from uuid import UUID
from typing import List
from pydantic import BaseModel
# Import the service we just created
from backend.doc_insighter.services.project_file_service import ProjectFileService
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
    - **category**: 'wsr', 'sow', 'techreview', etc.
    """
    # Validate category to prevent random strings (Optional but recommended)
    valid_categories = {'wsr', 'sow', 'codequality', 'bestpractices', 'techreview'}
    if category.lower() not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of {valid_categories}")

    # Call the service
    files = ProjectFileService.get_project_files(str(project_id), category)
    
    return files
# @router.get("/download/{project_id}/{filename}")
# def download_project_file(project_id: UUID, filename: str):
#     """
#     Download a specific file from the project folder.
#     """
#     # 1. Construct path: uploaded_docs/project_docs/{uuid}/{filename}
#     file_path = PROJECT_DOCUMENT_DIR / str(project_id) / filename

#     # 2. Check if file exists
#     if not file_path.exists():
#         raise HTTPException(status_code=404, detail="File not found")

#     # 3. Return the file
#     return FileResponse(
#         path=file_path, 
#         filename=filename, 
#         media_type='application/octet-stream'
#     )
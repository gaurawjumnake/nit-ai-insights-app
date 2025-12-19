from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

# 1. ROBUST PATH CALCULATION
# This ensures we find the 'backend' folder regardless of folder names like 'NIT-AI_INSIGHTS_APP'
# We start at this file and go up until we find the 'backend' directory
current_file = Path(__file__).resolve()
backend_dir = None

# Walk up the tree to find "backend"
for parent in current_file.parents:
    if parent.name == "backend":
        backend_dir = parent
        break

# Fallback if folder structure is weird
if not backend_dir:
    # Assume standard structure: app/api/simple_docs.py -> go up 3 levels
    backend_dir = current_file.parent.parent.parent

DOCS_DIR = backend_dir / "uploaded_docs" / "project_docs"

@router.get("/list-files")
def list_files():
    """
    Returns a list of files or a message if empty.
    """
    files_data = []
    
    # Check if directory exists
    if DOCS_DIR.exists():
        # Walk through the directory
        for path in DOCS_DIR.rglob("*"):
            if path.is_file():
                # Get path relative to the specific folder
                relative_path = path.relative_to(DOCS_DIR)
                
                # IMPORTANT: Replace backslashes (\) with forward slashes (/) for URLs
                # Windows paths use \, but URLs must use /
                clean_path = str(relative_path).replace("\\", "/")
                
                url = f"/static_docs/{clean_path}" 
                
                files_data.append({
                    "name": path.name,
                    "path": clean_path,
                    "url": url
                })

    # 2. HANDLE EMPTY FOLDER
    if not files_data:
        return {
            "status": "empty",
            "message": "No files to see",
            "files": []
        }

    return {
        "status": "success",
        "message": "Files retrieved",
        "files": files_data
    }
from fastapi import APIRouter
from pathlib import Path
from backend.app.services.file_scanner import ProjectFileScanner

router = APIRouter()

# --- 1. DYNAMIC PATH SETUP ---
# Find 'backend' folder automatically
current_file = Path(__file__).resolve()
backend_dir = None
for parent in current_file.parents:
    if parent.name == "backend":
        backend_dir = parent
        break
if not backend_dir:
    backend_dir = current_file.parent.parent.parent

# Define the Two Folders
UPLOAD_BASE = backend_dir / "uploaded_docs"
PMO_DIR = UPLOAD_BASE / "app_docs" / "pmo"
REVENUE_DIR = UPLOAD_BASE / "app_docs" / "revenue"

# --- 2. ENDPOINT: PMO ---
@router.get("/pmo-files")
def get_pmo_files():
    # We dynamically pass the PMO path and the PMO URL prefix
    scanner = ProjectFileScanner(directory=PMO_DIR, mount_point="/static_pmo")
    files = scanner.scan()
    
    return {
        "category": "PMO",
        "count": len(files),
        "files": files
    }

# --- 3. ENDPOINT: REVENUE ---
@router.get("/revenue-files")
def get_revenue_files():
    # We dynamically pass the Revenue path and the Revenue URL prefix
    scanner = ProjectFileScanner(directory=REVENUE_DIR, mount_point="/static_revenue")
    files = scanner.scan()
    
    return {
        "category": "Revenue",
        "count": len(files),
        "files": files
    }
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import UUID
from typing import Optional
import shutil

from typing import Callable, Any
from backend.app.db.session import get_db
from backend.app.services.import_service import ImportProjectData, ImportRevenueData
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
load_dotenv()


async def import_and_save_file(
    file: UploadFile,
    temp_dir: Path,
    success_dir: Path,
    failed_dir: Path,
    db : Session,
    import_function: Optional[Callable] = None,
    dry_run: bool = False,
    
) -> dict[str, Any]:
    """
    file import handler that saves files and processes them.
    
    Args:
        file: Uploaded file
        temp_dir: Temporary storage directory
        success_dir: Directory for successful imports
        failed_dir: Directory for failed imports
        import_function: Function to call for processing (should accept db, file_path, dry_run)
        db: Database session
        dry_run: Whether to run in dry-run mode
    """
    if file.content_type not in [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "text/csv",
        "application/csv",
    ]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload .xlsx or .csv")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    try:
        contents = await file.read()
        file_size = len(contents)
        
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large ({file_size / (1024*1024):.2f} MB). Maximum: 10 MB"
            )
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    temp_file_path = temp_dir / safe_filename
    
    try:
        with open(temp_file_path, "wb") as buffer:
            buffer.write(contents)
        print(f"✓ File saved to: {temp_file_path}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file to disk: {str(e)}"
        )
    
    if import_function:
        try:
            summary = import_function(db, contents, file.filename, dry_run)
            
            has_errors = summary.get("errors") and len(summary["errors"]) > 0
            import_successful = not has_errors and not dry_run
            
            if import_successful:
                final_file_path = success_dir / safe_filename
                shutil.move(str(temp_file_path), str(final_file_path))
                print(f"✓ File moved to success directory")
            elif not dry_run:
                final_file_path = failed_dir / safe_filename
                shutil.move(str(temp_file_path), str(final_file_path))
                print(f"✗ File moved to failed directory")
            else:
                if temp_file_path.exists():
                    temp_file_path.unlink()
                    print(f"✓ Dry run complete, temp file deleted")
            
            summary["uploaded_file"] = safe_filename
            summary["file_size_mb"] = round(file_size / (1024 * 1024), 2)
            summary["import_status"] = "success" if import_successful else ("dry_run" if dry_run else "failed")
            
            return summary
            
        except HTTPException:
            if temp_file_path.exists():
                shutil.move(str(temp_file_path), str(failed_dir / safe_filename))
            raise
        except Exception as e:
            if temp_file_path.exists():
                try:
                    shutil.move(str(temp_file_path), str(failed_dir / safe_filename))
                except:
                    pass
            raise HTTPException(status_code=400, detail=f"Failed to import: {str(e)}")
    else:
        return {}

async def import_and_save_document(
    file: UploadFile,
    document_type: str,
    project_id: UUID,
    temp_dir: Path,
    success_dir: Path,
    failed_dir: Path,
    db: Session,
    import_function: Optional[Callable] = None,
    dry_run: bool = False,
    
    
) -> dict[str, Any]:
    """
    File import handler that saves files and processes them.
    
    Args:
        file: Uploaded file
        temp_dir: Temporary storage directory
        success_dir: Directory for successful imports
        failed_dir: Directory for failed imports
        import_function: Function to call for processing (should accept db, file_path, dry_run)
        db: Database session
        dry_run: Whether to run in dry-run mode
    """
    if file.content_type not in [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "text/csv",
        "application/csv",
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/msword',
        'text/plain',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/pdf'
    ]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload .xlsx or .csv")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    try:
        contents = await file.read()
        file_size = len(contents)
        
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large ({file_size / (1024*1024):.2f} MB). Maximum: 10 MB"
            )
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{document_type}_{file.filename}"
    temp_file_path = temp_dir / safe_filename
    
    try:
        with open(temp_file_path, "wb") as buffer:
            buffer.write(contents)
        print(f"✓ File saved to: {temp_file_path}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file to disk: {str(e)}"
        )
    
    if import_function:
        try:

            summary = import_function(db=db, file_path=temp_file_path, project_id=project_id, dry_run=dry_run)
            
            has_errors = summary.get("errors") and len(summary["errors"]) > 0
            import_successful = not has_errors and not dry_run
            
            if import_successful:
                final_file_path = success_dir / safe_filename
                shutil.move(str(temp_file_path), str(final_file_path))
                print(f"✓ File moved to success directory")
            elif not dry_run:
                final_file_path = failed_dir / safe_filename
                shutil.move(str(temp_file_path), str(final_file_path))
                print(f"✗ File moved to failed directory")
            else:
                if temp_file_path.exists():
                    temp_file_path.unlink()
                    print(f"✓ Dry run complete, temp file deleted")
            
            summary["uploaded_file"] = safe_filename
            summary["file_size_mb"] = round(file_size / (1024 * 1024), 2)
            summary["import_status"] = "success" if import_successful else ("dry_run" if dry_run else "failed")
            
            return summary
            
        except HTTPException:
            if temp_file_path.exists():
                shutil.move(str(temp_file_path), str(failed_dir / safe_filename))
            raise
        except Exception as e:
            if temp_file_path.exists():
                try:
                    shutil.move(str(temp_file_path), str(failed_dir / safe_filename))
                except:
                    pass
            raise HTTPException(status_code=400, detail=f"Failed to import: {str(e)}")
    else:
        return {}
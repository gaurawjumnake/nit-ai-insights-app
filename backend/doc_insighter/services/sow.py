from sqlalchemy.orm import Session, joinedload
from sqlalchemy import UUID
from pathlib import Path
from typing import Any, Optional
from sqlalchemy.exc import IntegrityError
from backend.doc_insighter.core.extraction_pipeline import ProcessProjectDocument
from backend.doc_insighter.core.document_kpi_prompts import SOW
from backend.doc_insighter.tools.app_logger import Logger
from backend.app.models.document import ProjectDocument
log = Logger()

doc_processor = ProcessProjectDocument(SOW.prompt)

def get_project_document(db: Session, project_id: UUID, document_type:str) -> Optional[ProjectDocument]:
    """Retrieve a single revenue record by ID."""
    return db.query(ProjectDocument).options(
        joinedload(ProjectDocument.project)
    ).filter(ProjectDocument.project_id == project_id).first()

def process_document(db: Session, file_path: Path, project_id: UUID, dry_run: bool = False) -> dict[str, Any]:
    """Process SOW document and return summary dict"""
    
    document_type="SOW"

    if not file_path or not Path(file_path).exists():
        log.log_debug(f"File path not found - {file_path}")
        return {
            "errors": [f"Document file not found: {file_path}"],
            "records_processed": 0,
            "records_created": 0
        }
    
    content = doc_processor.run_doc_processor(file_path)
    if not content:
        log.log_error(f"Unable to Extract insights from document - {file_path}")
        content = ""

    if dry_run:
        return {
            "errors": [],
            "records_processed": 1,
            "records_created": 0,
            "message": "Dry run successful - document validated"
        }
    
    try:
        existing_doc = get_project_document(db, project_id, document_type)
        
        if existing_doc:
            existing_doc.content = content # type:ignore
            existing_doc.document_type = document_type # type:ignore
            doc_data = existing_doc
            operation = "updated"
            records_created = 0
        else:
            doc_data = ProjectDocument(
                project_id=project_id,
                content=content,
                document_type=document_type
            )
            db.add(doc_data)
            operation = "created"
            records_created = 1
        
        db.commit()
        db.refresh(doc_data)

        log.log_info(f"File processed successfully and {operation} in db")
        
        return {
            "errors": [],
            "records_processed": 1,
            "records_created": records_created,
            "document_id": str(doc_data.id),
            "operation": operation,
            "message": f"{document_type} document {operation} successfully"
        }
        
    except IntegrityError as e:
        db.rollback()
        log.log_warning(f"File not processed correctly. Error message - {e}")
        return {
            "errors": [f"Database integrity error: {str(e)}"],
            "records_processed": 1,
            "records_created": 0
        }
    except Exception as e:
        db.rollback()
        log.log_error(f"Unexpected error processing {document_type}: {e}")
        return {
            "errors": [f"Processing error: {str(e)}"],
            "records_processed": 1,
            "records_created": 0
        }

# # for testing -------------------------------------
# from backend.app.db.session import SessionLocal
# file_path = Path("test_data/sample sow.pdf")
# project_id ="561a6d34-08d4-4368-b203-1a5cc1e00d10"
# session = SessionLocal()
# result = process_sow(session, file_path, project_id) # type:ignore
# print(result)
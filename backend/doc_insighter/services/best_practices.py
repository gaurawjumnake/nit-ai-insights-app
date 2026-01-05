from sqlalchemy.orm import Session, joinedload
from sqlalchemy import UUID
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
from backend.doc_insighter.core.extraction_pipeline import ProcessProjectDocument
from backend.doc_insighter.tools.app_logger import Logger
from backend.app.models.document import ProjectDocument
from backend.doc_insighter.core.document_kpi_prompts import BestPractices

log = Logger()

# # 1. Define the Best Practices Audit Prompt
# class BestPractices:
#     prompt = """
#     Analyze the provided Engineering Guidelines or Process Document and generate a Best Practices Audit Report:
#         - Version Control Strategy: Evaluation of branching strategies (e.g., GitFlow, Trunk-based) and commit standards.
#         - Testing Maturity: Assessment of required testing layers (Unit, Integration, E2E) and coverage requirements.
#         - CI/CD & Automation: Analysis of deployment pipelines, automated checks, and release procedures.
#         - Code Review Standards: Evaluation of the peer review process, checklists, and approval requirements.
#         - Security & Compliance: Check for "Security by Design" principles, dependency scanning, and secret management policies.
#         - Documentation Standards: Requirements for API docs (Swagger), Readmes, and architecture decision records (ADRs).
#         - GAP ANALYSIS: Identify missing industry standards or areas where the process is manual/outdated.
#     """

# 2. Initialize the processor
doc_processor = ProcessProjectDocument(BestPractices.prompt)

def get_project_document(db: Session, project_id: UUID, document_type: str) -> Optional[ProjectDocument]:
    """Retrieve a single document record by ID and Type."""
    return db.query(ProjectDocument).options(
        joinedload(ProjectDocument.project)
    ).filter(
        ProjectDocument.project_id == project_id,
        ProjectDocument.document_type.ilike(document_type.lower())
    ).first()

def process_best_practices_document(db: Session, file_path: Path, project_id: UUID, dry_run: bool = False) -> dict[str, Any]:
    """Process a Best Practices/Guidelines document and return summary dict"""
    
    # DISTINCT DOCUMENT TYPE
    document_type = "BEST_PRACTICES"

    if not file_path or not Path(file_path).exists():
        log.log_debug(f"File path not found - {file_path}")
        return {
            "errors": [f"Document file not found: {file_path}"],
            "records_processed": 0,
            "records_created": 0
        }
    
    # Run the LLM Processor
    content = doc_processor.run_doc_processor(file_path)
    
    if not content:
        log.log_error(f"Unable to Extract insights from document - {file_path}")
        content = ""

    if dry_run:
        return {
            "errors": [],
            "records_processed": 1,
            "records_created": 0,
            "message": "Dry run successful - Best Practices audit generated (not saved)"
        }
    
    try:
        # Check if a report already exists for this project
        existing_doc = get_project_document(db, project_id, document_type)
        
        if existing_doc:
            existing_doc.content = content # type:ignore
            existing_doc.document_type = document_type # type:ignore
            doc_data = existing_doc
            operation = "updated"
            records_created = 0
        else:
            doc_data = ProjectDocument(
                id=uuid4(),
                project_id=project_id,
                content=content,
                document_type=document_type
            )
            db.add(doc_data)
            operation = "created"
            records_created = 1
        
        db.commit()
        db.refresh(doc_data)

        log.log_info(f"Best Practices document processed successfully and {operation} in db")
        
        return {
            "errors": [],
            "records_processed": 1,
            "records_created": records_created,
            "document_id": str(doc_data.id),
            "operation": operation,
            "message": f"{document_type} report {operation} successfully"
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
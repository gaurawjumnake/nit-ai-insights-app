from sqlalchemy.orm import Session, joinedload
from sqlalchemy import UUID
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
from backend.doc_insighter.core.extraction_pipeline import ProcessProjectDocument
from backend.doc_insighter.tools.app_logger import Logger
from backend.app.models.document import ProjectDocument

log = Logger()

# 1. Define the Tech Review Prompt
class TechReview:
    prompt = """
    Analyze the provided technical document and extract key insights for a Technical Review Report:
        - Proposed Architecture and Design Patterns (e.g., Microservices vs Monolith)
        - Technology Stack Assessment (Suitability of languages, frameworks, and databases)
        - Scalability and High Availability Strategy (Load balancing, caching, replication)
        - Integration Interfaces (API standards, external system dependencies)
        - Security and Compliance (Authentication, authorization, data encryption)
        - Infrastructure and DevOps (Deployment strategy, CI/CD, containerization)
        - Critical Technical Risks and Single Points of Failure
    """

# 2. Initialize the processor
doc_processor = ProcessProjectDocument(TechReview.prompt)

def get_project_document(db: Session, project_id: UUID, document_type: str) -> Optional[ProjectDocument]:
    """Retrieve a single document record by ID and Type."""
    return db.query(ProjectDocument).options(
        joinedload(ProjectDocument.project)
    ).filter(
        ProjectDocument.project_id == project_id,
        ProjectDocument.document_type.ilike(document_type.lower())
    ).first()

def process_tech_review_document(db: Session, file_path: Path, project_id: UUID, dry_run: bool = False) -> dict[str, Any]:
    """Process Technical Design document and return summary dict"""
    
    # DISTINCT DOCUMENT TYPE
    document_type = "TECH_REVIEW"

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
            "message": "Dry run successful - Tech Review analysis generated (not saved)"
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

        log.log_info(f"Tech Review file processed successfully and {operation} in db")
        
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
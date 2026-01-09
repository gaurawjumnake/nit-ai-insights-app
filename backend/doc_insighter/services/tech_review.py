from sqlalchemy.orm import Session, joinedload
from sqlalchemy import UUID
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone, timedelta

from backend.doc_insighter.core.extraction_pipeline import ProcessProjectDocument
from backend.doc_insighter.core.document_kpi_prompts import TechReview
from backend.doc_insighter.tools.app_logger import Logger
from backend.app.models.document import ProjectDocument

log = Logger()

# IST timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

doc_processor = ProcessProjectDocument(TechReview.prompt)


def get_project_document(
    db: Session,
    project_id: UUID,
    document_type: str
) -> Optional[ProjectDocument]:
    """Retrieve document by project and type"""
    return (
        db.query(ProjectDocument)
        .options(joinedload(ProjectDocument.project))
        .filter(
            ProjectDocument.project_id == project_id,
            ProjectDocument.document_type.ilike(document_type.lower()),
        )
        .first()
    )


def process_tech_review_document(
    db: Session,
    file_path: Path,
    project_id: UUID,
    dry_run: bool = False
) -> dict[str, Any]:
    """Process Tech Review document"""

    document_type = "TECH_REVIEW"

    if not file_path or not Path(file_path).exists():
        log.log_debug(f"File path not found - {file_path}")
        return {
            "errors": [f"Document file not found: {file_path}"],
            "records_processed": 0,
            "records_created": 0
        }

    content = doc_processor.run_doc_processor(file_path)
    if not content:
        log.log_error(f"Unable to extract insights from document - {file_path}")
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
            existing_doc.content = content  # type: ignore
            existing_doc.document_type = document_type  # type: ignore
            doc_data = existing_doc
            operation = "updated"
            records_created = 0
        else:
            ist_time = datetime.now(IST).replace(tzinfo=None)
            doc_data = ProjectDocument(
                id=uuid4(),
                project_id=project_id,
                content=content,
                document_type=document_type,
                created_at=ist_time
            )
            db.add(doc_data)
            operation = "created"
            records_created = 1

        db.commit()
        db.refresh(doc_data)

        log.log_info(f"Tech Review document {operation} successfully")

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
        log.log_warning(f"Database integrity error - {e}")
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

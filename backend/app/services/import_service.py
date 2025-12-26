import io,re
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import or_, text
from uuid import uuid4
import datetime
from typing import Dict, Any, Optional, List
from backend.doc_insighter.tools.app_logger import Logger
log = Logger()
from backend.app.models.account import Account
from backend.app.models.project import Project
from backend.app.models.delivery_unit import DeliveryUnit
from backend.app.models.revenue import RevenueMaster
from backend.app.models.document import ProjectDocument
from backend.utitlites.app_utilites import safe_float, safe_int
from rapidfuzz import fuzz

class ImportProjectData:
    def __init__(self) -> None:
        self.EXPECTED_COLUMNS = [
            "project_name",
            "account_name", 
            "start_date",
            "end_date",
            "department",  
            "account_manager",
            "status",
            "project_type"
        ]

    def _scalar(self, value):
        if isinstance(value, pd.Series):
            for v in value.tolist():
                if pd.notna(v) and v is not None:
                    value = v
                    break
            else:
                return ""
        if isinstance(value, (list, tuple)):
            for v in value:
                if pd.notna(v) and v is not None:
                    value = v
                    break
            else:
                return ""
        if isinstance(value, float) and pd.isna(value):
            return ""
        return str(value).strip() if value is not None else ""

    def _get_or_create_delivery_unit(self, db: Session, row: Dict[str, Any]) -> Optional[DeliveryUnit]:
        """Get or create delivery unit from department name."""
        du_name = (
            self._scalar(row.get("department", "")) or 
            self._scalar(row.get("delivery_unit_name", "")) or
            self._scalar(row.get("delivery_unit", ""))
        )
        
        if not du_name:
            log.log_error("⚠ Warning: No department specified")
            return None
        
        try:
            delivery_unit = db.query(DeliveryUnit).filter(
                DeliveryUnit.name.ilike(du_name)
            ).first()
            
            if delivery_unit:
                log.log_info(f"✓ Found delivery unit: {delivery_unit.name}")
                return delivery_unit

            log.log_info(f"✓ Creating new delivery unit: {du_name}")
            new_du = DeliveryUnit(id=uuid4(), name=du_name)
            db.add(new_du)
            db.flush()
            return new_du
            
        except Exception as e:
            log.log_error(f"✗ Error processing delivery unit '{du_name}': {e}")
            return None

    def _get_or_create_account(
        self, 
        db: Session, 
        row: Dict[str, Any],
        delivery_unit: DeliveryUnit
    ) -> Optional[Account]:
        account_name = self._scalar(row.get("account_name", ""))
        if not account_name:
            log.log_error("✗ Missing account_name")
            return None

        try:
            account = db.query(Account).filter(
                Account.name.ilike(account_name)
            ).first()
            
            if account:
                log.log_info(f"✓ Found account: {account.name}")
                if delivery_unit and account.delivery_unit_id != delivery_unit.id: #type:ignore
                    account.delivery_unit_id = delivery_unit.id
                    db.add(account)
                    db.flush()
                return account
            
            log.log_info(f"✓ Creating new account: {account_name}")
            new_account = Account(
                id=uuid4(),
                name=account_name,
                delivery_unit_id=delivery_unit.id,
                account_manager=self._scalar(row.get("account_manager", ""))
            )
            db.add(new_account)
            db.flush()
            return new_account
            
        except Exception as e:
            log.log_error(f"✗ Error processing account '{account_name}': {e}")
            return None

    def _create_or_update_revenue_record(
        self, 
        db: Session, 
        project: Project, 
        row: Dict[str, Any], 
        dry_run: bool = False
    ) -> str:
        """Create or update revenue record. Returns 'created', 'updated', or 'skipped'."""
        try:
            existing_revenue = db.query(RevenueMaster).filter(
                RevenueMaster.project_id == project.id,
            ).first()

            expected_revenue = float(row.get("expected_revenue", 0) or 0)
            ytd_revenue = float(row.get("ytd_revenue", 0) or 0)
            ai_direct_people = int(float(row.get("ai_direct_people", 0) or 0))
            ai_assisted_people = int(float(row.get("ai_assisted_people", 0) or 0))
            ai_revenue = float(row.get("ai_direct_revenue", 0) or row.get("ai_revenue", 0) or 0)
            ai_assisted_revenue = float(row.get("ai_assisted_revenue", 0) or 0)
            
            total_ai_revenue = ai_revenue + ai_assisted_revenue
            
            file_total_revenue = row.get("total_revenue")
            if file_total_revenue is not None and str(file_total_revenue).strip():
                try:
                    total_revenue = float(str(file_total_revenue))
                except ValueError:
                    total_revenue = ytd_revenue if ytd_revenue > 0 else expected_revenue
            else:
                total_revenue = ytd_revenue if ytd_revenue > 0 else expected_revenue
            
            start_date = pd.to_datetime(row.get("start_date"), errors='coerce') # type:ignore
            if pd.isna(start_date):
                start_date = project.from_date
            
            end_date = pd.to_datetime(row.get("end_date"), errors='coerce') # type:ignore
            if pd.isna(end_date):
                end_date = project.to_date

            status = self._scalar(row.get("status", "active")) or "active"
            collection_date =  "1900-01-01 00:00:00" # type:ignore

            if existing_revenue:
                if not dry_run:
                    existing_revenue.project_name = project.name  # type:ignore
                    existing_revenue.expected_revenue = expected_revenue  # type:ignore
                    existing_revenue.ytd_revenue = ytd_revenue  # type:ignore
                    existing_revenue.ai_direct_revenue = ai_revenue  # type:ignore
                    existing_revenue.ai_direct_people = ai_direct_people  # type:ignore
                    existing_revenue.ai_assisted_people = ai_assisted_people  # type:ignore
                    existing_revenue.ai_assisted_revenue = ai_assisted_revenue  # type:ignore
                    existing_revenue.total_ai_revenue = total_ai_revenue  # type:ignore
                    existing_revenue.total_revenue = total_revenue  # type:ignore
                    existing_revenue.from_date = start_date
                    existing_revenue.to_date = end_date
                    existing_revenue.status = status  # type:ignore
                    existing_revenue.collection_date = collection_date # type:ignore
                    db.add(existing_revenue)
                    db.flush()
                return "updated"
            else:
                if not dry_run:
                    new_revenue = RevenueMaster(
                        id = uuid4(),
                        project_id=project.id,
                        project_name=project.name,
                        expected_revenue=expected_revenue,
                        ytd_revenue=ytd_revenue,
                        ai_direct_revenue=ai_revenue,
                        ai_direct_people=ai_direct_people,
                        ai_assisted_people=ai_assisted_people,
                        ai_assisted_revenue=ai_assisted_revenue,
                        total_ai_revenue=total_ai_revenue,
                        total_revenue=total_revenue,
                        from_date=start_date,
                        to_date=end_date,
                        status=status,
                        collection_date = collection_date
                    )
                    db.add(new_revenue)
                    db.flush()
                return "created"
        except Exception as e:
            log.log_error(f"✗ Error managing revenue for {project.name}: {e}")
            return "skipped"

    def _get_or_create_project_document(
        self, 
        db: Session, 
        project: Project,
        row: Dict[str, Any]
    ) -> Optional[ProjectDocument]:
        try:
            content = self._scalar(row.get("content", "")) or self._scalar(row.get("document_content", ""))
            document_type = self._scalar(row.get("document_type", "")) or self._scalar(row.get("doc_type", ""))

            existing_doc = db.query(ProjectDocument).filter(
                ProjectDocument.project_id == project.id
            ).first()
            
            if existing_doc:
                log.log_info(f"Found existing document for project: {project.name}")
                if content:
                    existing_doc.content = content  # type:ignore
                if document_type:
                    existing_doc.document_type = document_type  # type:ignore
                db.add(existing_doc)
                db.flush()
                return existing_doc

            log.log_info(f"Creating new document for project: {project.name}")
            new_doc = ProjectDocument(
                id=uuid4(),
                project_id=project.id,
                content=content if content else None,
                document_type=document_type if document_type else None
            )
            db.add(new_doc)
            db.flush()
            return new_doc
            
        except Exception as e:
            log.log_error(f"✗ Error processing document for project '{project.name}': {e}")
            return None

    def import_projects_from_file(
        self, 
        db: Session, 
        content: bytes, 
        filename: str, 
        dry_run: bool = False
    ):
        try:
            if filename.lower().endswith(".csv"):
                df = pd.read_csv(io.BytesIO(content))
            elif filename.lower().endswith((".xlsx", ".xls")):
                df = pd.read_excel(io.BytesIO(content), engine='openpyxl')
            else:
                raise ValueError("File must be CSV or Excel (.xlsx, .xls)")
        except Exception as e:
            raise ValueError(f"Failed to read file: {str(e)}")

        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        log.log_info(f"Columns: {list(df.columns)}")

        ALIASES={
            "project_name": ["project_name", "project", "project_n", "project name","Project Name"],
            "account_name": ["account_name","account","account_n","account name","Account Name"],
            "start_date": ["start date","Start date"],
            "end_date": ["end date"," End date"],
            "delivery_unit_name": ["department","Delivery Unit","delivery unit","delivery_unit"],
            "account_manager": ["Account Manager","Account manager"],
            "status": ["Status"],
            "project_type": ["Project Type","Project type"]
        }

        normalized_aliases = {}
        for canonical, aliases in ALIASES.items():
            normalized_aliases[canonical] = [a.strip().lower().replace(" ", "_") for a in aliases]

        canonical_cols = {}
        threshold = 80

        for col in df.columns:
            best_match = None
            best_score = 0
            best_canonical = None

            for canonical, aliases in normalized_aliases.items():
                for alias in aliases:
                    score = fuzz.ratio(col, alias)
                    if score > best_score:
                        best_score = score
                        best_match = alias
                        best_canonical = canonical

            if best_score >= threshold:
                canonical_cols[col] = best_canonical
                log.log_info(f"Matched '{col}' -> '{best_canonical}' (score: {best_score})")
            else:
                canonical_cols[col] = col
                log.log_info(f"No match for '{col}', keeping original")

        df.rename(columns=canonical_cols, inplace=True)
        log.log_info(f"Final columns: {list(df.columns)}")

        def normalize_du_value(text):
            if not isinstance(text, (str, int, float)):
                return text
            
            clean_text = str(text).strip()

            if re.search(r'(?:du|unit|dept)[\W_]*1', clean_text, re.IGNORECASE):
                return 'DU1'
            
            # Covers: "delivery_unit_2", "du2", "Delivery Unit - 2"
            if re.search(r'(?:du|unit|dept)[\W_]*2', clean_text, re.IGNORECASE):
                return 'DU2'
            
            # Covers: "Delivery Unit 3", "du-3", "delivery_unit - 3"
            if re.search(r'(?:du|unit|dept)[\W_]*3', clean_text, re.IGNORECASE):
                return 'DU3'
                
            return clean_text
        
        if "delivery_unit_name" in df.columns:
            log.log_info("✓ Processing Delivery Unit Normalization...")
            df["delivery_unit_name"] = df["delivery_unit_name"].apply(normalize_du_value)
        else:
            log.log_warning("WARNING: Could not find 'delivery_unit' column to normalize.")

        required = {"project_name", "account_name"}
        if not required.issubset(set(df.columns)):
            missing = required - set(df.columns)
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        created_accounts = 0
        updated_accounts = 0
        created_projects = 0
        updated_projects = 0
        created_revenue_records = 0
        updated_revenue_records = 0
        created_documents = 0
        updated_documents = 0
        skipped_rows = 0
        errors = []

        for idx, row in df.iterrows():
            try:
                delivery_unit = self._get_or_create_delivery_unit(db, row)  # type:ignore

                account = self._get_or_create_account(db, row, delivery_unit)  # type:ignore
                if not account:
                    log.log_error(f"✗ Skipping row - no account")
                    skipped_rows += 1
                    continue

                if account.created_at is None:
                    created_accounts += 1
                else:
                    updated_accounts += 1

                project_name = self._scalar(row.get("project_name", ""))
                if not project_name:
                    log.log_error(f"✗ Missing project_name")
                    skipped_rows += 1
                    continue

                start_date = pd.to_datetime(row.get("start_date"), errors='coerce')  # type:ignore
                if pd.isna(start_date):
                    start_date = None
                
                end_date = pd.to_datetime(row.get("end_date"), errors='coerce')  # type:ignore
                if pd.isna(end_date):
                    end_date = None

                status = self._scalar(row.get("status", "active")) or "active"
                project_type = self._scalar(row.get("project_type")) or None

                existing_project = db.query(Project).filter(
                    Project.name.ilike(project_name), 
                    Project.account_id == account.id
                ).first()

                if existing_project:
                    log.log_info(f"✓ Found existing project: {project_name}")
                    if not dry_run:
                        existing_project.status = status  # type:ignore
                        existing_project.delivery_unit_id = delivery_unit.id  # type:ignore
                        existing_project.project_type = project_type  # type:ignore
                        existing_project.from_date = start_date  # type:ignore
                        existing_project.to_date = end_date  # type:ignore
                        db.add(existing_project)
                        db.flush()

                        revenue_action = self._create_or_update_revenue_record(
                            db, existing_project, row, dry_run=False # type:ignore
                        )  
                        if revenue_action == "created":
                            created_revenue_records += 1
                        elif revenue_action == "updated":
                            updated_revenue_records += 1

                        doc_result = self._get_or_create_project_document(
                            db, existing_project, row  # type:ignore
                        )
                        if doc_result:
                            existing_doc_check = db.query(ProjectDocument).filter(
                                ProjectDocument.id == doc_result.id,
                                ProjectDocument.created_at >= datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=5)
                            ).first()
                            if existing_doc_check:
                                created_documents += 1
                            else:
                                updated_documents += 1
                    
                    updated_projects += 1
                else:
                    log.log_info(f"✓ Creating new project: {project_name}")
                    new_project = Project(
                        name=project_name,
                        account_id=account.id,
                        delivery_unit_id = delivery_unit.id,  # type:ignore
                        status=status,
                        project_type=project_type,
                        from_date=start_date,
                        to_date=end_date
                    )
                    
                    if not dry_run:
                        db.add(new_project)
                        db.flush()

                        revenue_action = self._create_or_update_revenue_record(
                            db, new_project, row, dry_run=False   # type:ignore
                        ) 
                        if revenue_action == "created":
                            created_revenue_records += 1
                        elif revenue_action == "updated":
                            updated_revenue_records += 1

                        doc_result = self._get_or_create_project_document(
                            db, new_project, row  # type:ignore
                        )
                        if doc_result:
                            created_documents += 1
                    
                    created_projects += 1

            except Exception as e:
                error_msg = f"Row {idx + 1}: {str(e)}"   # type:ignore
                log.log_error(f"{error_msg}")
                errors.append(error_msg)
                db.rollback()
                skipped_rows += 1
                continue

        if not dry_run:
            try:
                db.commit()
                try:
                    db.execute(text("SELECT refresh_account_metrics_mv();"))
                    db.commit()
                except Exception as e:
                    log.log_error(f"Warning: Failed to refresh metrics: {e}")
                log.log_info("\nSuccessfully committed all changes")
            except Exception as e:
                db.rollback()
                error_msg = f"Final commit failed: {str(e)}"
                log.log_error(f"✗ {error_msg}")
                errors.append(error_msg)

        return {
            "rows": len(df),
            "created_accounts": created_accounts,
            "updated_accounts": updated_accounts,
            "created_projects": created_projects,
            "updated_projects": updated_projects,
            "created_revenue_records": created_revenue_records,
            "updated_revenue_records": updated_revenue_records,
            "created_documents": created_documents,
            "updated_documents": updated_documents,
            "skipped_rows": skipped_rows,
            "errors": errors,
            "expected_columns": self.EXPECTED_COLUMNS,
        }

class ImportRevenueData:
    def __init__(self) -> None:
        self.EXPECTED_COLUMNS = [
            "project_name",
            "ai_direct_revenue",
            "ai_assisted_revenue"
        ]

    def _scalar(self, value):
        """Return a clean scalar string/number from potentially messy cell values."""
        if isinstance(value, pd.Series):
            for v in value.tolist():
                if pd.notna(v) and v is not None:
                    value = v
                    break
            else:
                return ""
        if isinstance(value, (list, tuple)):
            for v in value:
                if pd.notna(v) and v is not None:
                    value = v
                    break
            else:
                return ""
        if isinstance(value, float) and pd.isna(value):
            return ""
        return str(value).strip() if value is not None else ""

    def import_revenue_from_file(
        self, 
        db: Session, 
        content: bytes, 
        filename: str, 
        dry_run: bool = False
    ):

        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))

        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        log.log_info(f"Columns: {list(df.columns)}")

        ALIASES = {
            "project_name": ["project_name", "project", "project_n", "project name"],
            "expected_revenue": ["expected_revenue", "expected_", "expected"],
            "ytd_revenue": ["ytd_revenue", "ytd_reven", "ytd"],
            "ai_direct_people": ["ai_direct_people", "ai_direct_peo", "ai_direct_p"],
            "ai_assisted_people": ["ai_assisted_people", "ai_assiste_peo", "ai_assisted_p"],
            "ai_direct_revenue": ["ai_direct_revenue", "ai_direct_r", "ai_direct", "ai_revenue"],
            "ai_assisted_revenue": ["ai_assisted_revenue", "ai_assiste_r", "ai_assisted"],
            "from_date": ["from_date", "start_date", "start"],
            "to_date": ["to_date", "end_date", "end"],
            "status": ["status"],
            "total_revenue": ["total_revenue", "total_rev", "total"]
        }

        normalized_aliases = {}
        for canonical, aliases in ALIASES.items():
            normalized_aliases[canonical] = [a.strip().lower().replace(" ", "_") for a in aliases]

        canonical_cols = {}
        threshold = 80

        for col in df.columns:
            best_match = None
            best_score = 0
            best_canonical = None

            for canonical, aliases in normalized_aliases.items():
                for alias in aliases:
                    score = fuzz.ratio(col, alias)
                    if score > best_score:
                        best_score = score
                        best_match = alias
                        best_canonical = canonical

            if best_score >= threshold:
                canonical_cols[col] = best_canonical
                log.log_info(f"Matched '{col}' -> '{best_canonical}' (score: {best_score})")
            else:
                canonical_cols[col] = col
                log.log_info(f"No match for '{col}', keeping original")

        df.rename(columns=canonical_cols, inplace=True)
        log.log_info(f"Final columns: {list(df.columns)}")

        required = {"project_name"}
        if not required.issubset(set(df.columns)):
            missing = required - set(df.columns)
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        created_revenue = 0
        updated_revenue = 0
        skipped_rows = 0

        for _, row in df.iterrows():
            project_name = self._scalar(row.get("project_name", ""))
            log.log_info(f"Parsing Revenue data for :- {project_name}")
            
            if not project_name:
                log.log_error(f"Warning: Missing project_name. Skipping row.")
                skipped_rows += 1
                continue

            project = db.query(Project).filter(
                Project.name.ilike(project_name)
            ).first()
            
            if not project:
                log.log_debug(f"Warning: Project '{project_name}' not found. Skipping row.")
                skipped_rows += 1
                continue

            expected_revenue = safe_float(str(row.get("expected_revenue", 0.0)))
            ytd_revenue = safe_float(str(row.get("ytd_revenue", 0.0)))
            ai_direct_people = safe_int(row.get("ai_direct_people", 0))
            ai_assisted_people = safe_int(row.get("ai_assisted_people", 0))
            ai_direct_revenue = safe_float(str(row.get("ai_direct_revenue", 0.0)))
            ai_assisted_revenue = safe_float(str(row.get("ai_assisted_revenue", 0.0)))
            
            total_ai_revenue = ai_direct_revenue + ai_assisted_revenue
            
            file_total_revenue = row.get("total_revenue")
            if file_total_revenue is not None and str(file_total_revenue).strip():
                total_revenue = float(str(file_total_revenue))
            elif ytd_revenue > 0:
                total_revenue = ytd_revenue  
            elif expected_revenue > 0:
                total_revenue = expected_revenue
            else:
                total_revenue = 0.0

            from_date = pd.to_datetime(row.get("from_date"), errors='coerce') #type:ignore
            if pd.isna(from_date):
                from_date = None
            
            to_date = pd.to_datetime(row.get("to_date"), errors='coerce') #type:ignore
            if pd.isna(to_date):
                to_date = None
            
            collection_date = pd.to_datetime(row.get("collection_date"), errors='coerce') #type:ignore
            if pd.isna(collection_date):
                collection_date = None

            existing_revenue = db.query(RevenueMaster).filter(
                RevenueMaster.project_id == project.id,
                or_(
                    RevenueMaster.collection_date == collection_date,
                    RevenueMaster.collection_date.is_(None)
                    )
            ).first()

            if existing_revenue:
                if not dry_run:
                    existing_revenue.project_name = project.name #type:ignore
                    existing_revenue.expected_revenue = expected_revenue #type:ignore
                    existing_revenue.ytd_revenue = ytd_revenue #type:ignore
                    existing_revenue.ai_direct_revenue = ai_direct_revenue #type:ignore
                    existing_revenue.ai_direct_people = ai_direct_people #type:ignore
                    existing_revenue.ai_assisted_people = ai_assisted_people #type:ignore
                    existing_revenue.ai_assisted_revenue = ai_assisted_revenue #type:ignore
                    existing_revenue.total_ai_revenue = total_ai_revenue #type:ignore
                    existing_revenue.total_revenue = total_revenue #type:ignore
                    existing_revenue.from_date = project.from_date #type:ignore
                    existing_revenue.to_date = project.to_date #type:ignore
                    existing_revenue.status = project.status #type:ignore
                    existing_revenue.collection_date = collection_date #type:ignore
                    db.add(existing_revenue)
                updated_revenue += 1
                log.log_info(f"Found existing project. Updating data")
            else:
                # Create new revenue record
                if not dry_run:
                    new_revenue = RevenueMaster(
                        id = uuid4(),
                        project_id=project.id,
                        project_name=project.name,
                        expected_revenue=expected_revenue,
                        ytd_revenue=ytd_revenue,
                        ai_direct_revenue=ai_direct_revenue,
                        ai_direct_people=ai_direct_people,
                        ai_assisted_people=ai_assisted_people,
                        ai_assisted_revenue=ai_assisted_revenue,
                        total_ai_revenue=total_ai_revenue,
                        total_revenue=total_revenue,
                        from_date=project.from_date,
                        to_date=project.to_date,
                        status=project.status,
                        collection_date = collection_date
                    )
                    db.add(new_revenue)
                log.log_info(f"Missing Project. Creating new revenue record")
                created_revenue += 1

        if not dry_run:
            try:
                db.commit()
                try:
                    db.execute(text("SELECT refresh_account_metrics_mv();"))
                    db.commit()
                except Exception as e:
                    log.log_warning(f"Warning: Failed to refresh metrics: {e}")
            except Exception as e:
                db.rollback()
                log.log_error(f"Final commit failed: {e}")
        
        stats = {
            "rows": len(df),
            "created_revenue": created_revenue,
            "updated_revenue": updated_revenue,
            "skipped_rows": skipped_rows,
            "expected_columns": self.EXPECTED_COLUMNS,
        }
        log.log_info(f"Updated revenue master:- \n {stats}")
        return stats

# Testing Area ----------------------------------------------------------------------------------------------

# summary = MasterSummary()
# db = SessionLocal()
# response = summary.get_project_level_summary(db)
# print(response)

# from backend.app.db.session import SessionLocal
# db = SessionLocal()

# importer = ImportProjectData()
# fname = "backend/uploaded_docs/app_docs/pmo/20251226_190104_project_ledger.xlsx"
# with open(fname, 'rb') as f:
#     file_content = f.read()

# result = importer.import_projects_from_file(
#     db=db, 
#     content=file_content, 
#     filename="projects.xlsx",
#     dry_run=False
# )

# importer = ImportRevenueData()
# fname = "test_data/matched_names (2).xlsx"
# with open(fname, 'rb') as f:
#     file_content = f.read()

# result = importer.import_revenue_from_file(db, file_content, "revenue.xlsx")

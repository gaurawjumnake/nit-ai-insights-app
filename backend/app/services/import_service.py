import io
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_, or_
from uuid import uuid4
from typing import Dict, Any, Optional, List
from decimal import Decimal
from backend.ai_engine.tools.app_logger import Logger
log = Logger()
from backend.app.services.project import create_project
from backend.app.models.account import Account
from backend.app.models.project import Project
from backend.app.models.delivery_unit import DeliveryUnit
from backend.app.models.revenue import RevenueMaster
from backend.app.schemas.project import ProjectSummary
from backend.app.schemas.dashboard import DashboardStatsOut
from backend.ai_engine.tools.app_logger import Logger
log = Logger()
from backend.app.db.session import get_db, SessionLocal
from uuid import UUID as _UUID
import pandas as pd
from sqlalchemy import MetaData, Table, select, insert

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
            print("⚠ Warning: No department specified")
            return None
        
        try:
            delivery_unit = db.query(DeliveryUnit).filter(
                DeliveryUnit.name.ilike(du_name)
            ).first()
            
            if delivery_unit:
                print(f"✓ Found delivery unit: {delivery_unit.name}")
                return delivery_unit

            print(f"✓ Creating new delivery unit: {du_name}")
            new_du = DeliveryUnit(id=uuid4(), name=du_name)
            db.add(new_du)
            db.flush()
            return new_du
            
        except Exception as e:
            print(f"✗ Error processing delivery unit '{du_name}': {e}")
            return None

    def _get_or_create_account(
        self, 
        db: Session, 
        row: Dict[str, Any],
        delivery_unit: DeliveryUnit
    ) -> Optional[Account]:
        """Get or create account."""
        account_name = self._scalar(row.get("account_name", ""))
        if not account_name:
            print("✗ Missing account_name")
            return None

        try:
            account = db.query(Account).filter(
                Account.name.ilike(account_name)
            ).first()
            
            if account:
                print(f"✓ Found account: {account.name}")
                if delivery_unit and account.delivery_unit_id != delivery_unit.id: #type:ignore
                    account.delivery_unit_id = delivery_unit.id
                    db.add(account)
                    db.flush()
                return account
            
            print(f"✓ Creating new account: {account_name}")
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
            print(f"✗ Error processing account '{account_name}': {e}")
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
            print(f"✗ Error managing revenue for {project.name}: {e}")
            return "skipped"

    def import_projects_from_file(
        self, 
        db: Session, 
        content: bytes, 
        filename: str, 
        dry_run: bool = False
    ):
        """Import projects from Excel/CSV and create/update revenue records."""
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
        print(f"Columns: {list(df.columns)}")

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
        skipped_rows = 0
        errors = []

        for idx, row in df.iterrows():
            try:
                delivery_unit = self._get_or_create_delivery_unit(db, row)  # type:ignore

                account = self._get_or_create_account(db, row, delivery_unit)  # type:ignore
                if not account:
                    print(f"✗ Skipping row - no account")
                    skipped_rows += 1
                    continue

                if account.created_at is None:
                    created_accounts += 1
                else:
                    updated_accounts += 1

                project_name = self._scalar(row.get("project_name", ""))
                if not project_name:
                    print(f"✗ Missing project_name")
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
                    print(f"✓ Found existing project: {project_name}")
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
                    
                    updated_projects += 1
                else:
                    print(f"✓ Creating new project: {project_name}")
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
                    
                    created_projects += 1

            except Exception as e:
                error_msg = f"Row {idx + 1}: {str(e)}"   # type:ignore
                print(f"✗ {error_msg}")
                errors.append(error_msg)
                # IMPORTANT: Rollback only this row's transaction
                db.rollback()
                skipped_rows += 1
                continue

        if not dry_run:
            try:
                db.commit()
                print("\n✅ Successfully committed all changes")
            except Exception as e:
                db.rollback()
                error_msg = f"Final commit failed: {str(e)}"
                print(f"✗ {error_msg}")
                errors.append(error_msg)

        return {
            "rows": len(df),
            "created_accounts": created_accounts,
            "updated_accounts": updated_accounts,
            "created_projects": created_projects,
            "updated_projects": updated_projects,
            "created_revenue_records": created_revenue_records,
            "updated_revenue_records": updated_revenue_records,
            "skipped_rows": skipped_rows,
            "errors": errors,
            "expected_columns": self.EXPECTED_COLUMNS,
        }

class ImportRevenueData:
    def __init__(self) -> None:
        # Simplified columns - only project_name and AI revenue fields are required
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

        raw_cols = [c.strip().lower().replace(" ", "_") for c in df.columns]

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

        canonical_cols = {}
        for col in raw_cols:
            matched = False
            for canonical, aliases in ALIASES.items():
                for alias in aliases:
                    if col == alias or col.startswith(alias):
                        canonical_cols[col] = canonical
                        matched = True
                        break
                if matched:
                    break
            if not matched:
                canonical_cols[col] = col

        rename_dict = {orig: canon for orig, canon in canonical_cols.items() if orig != canon}
        df.columns = raw_cols
        if rename_dict:
            df = df.rename(columns=rename_dict)

        required = {"project_name"}
        if not required.issubset(set(df.columns)):
            missing = required - set(df.columns)
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        created_revenue = 0
        updated_revenue = 0
        skipped_rows = 0

        for _, row in df.iterrows():
            project_name = self._scalar(row.get("project_name", ""))
            
            if not project_name:
                print(f"Warning: Missing project_name. Skipping row.")
                skipped_rows += 1
                continue

            project = db.query(Project).filter(
                Project.name.ilike(project_name)
            ).first()
            
            if not project:
                print(f"Warning: Project '{project_name}' not found. Skipping row.")
                skipped_rows += 1
                continue

            expected_revenue = float(str(row.get("expected_revenue", 0) or 0))
            ytd_revenue = float(str(row.get("ytd_revenue", 0) or 0))
            ai_direct_people = int(row.get("ai_direct_people", 0) or 0)
            ai_assisted_people = int(row.get("ai_assisted_people", 0) or 0)
            ai_direct_revenue = float(str(row.get("ai_direct_revenue", 0) or 0))
            ai_assisted_revenue = float(str(row.get("ai_assisted_revenue", 0) or 0))
            
            total_ai_revenue = ai_direct_revenue + ai_assisted_revenue
            
            file_total_revenue = row.get("total_revenue")
            if file_total_revenue is not None and str(file_total_revenue).strip():
                total_revenue = float(str(file_total_revenue))
            else:
                total_revenue = ytd_revenue if ytd_revenue > 0 else expected_revenue

            from_date = pd.to_datetime(row.get("from_date"), errors='coerce') #type:ignore
            if pd.isna(from_date):
                from_date = None
            
            to_date = pd.to_datetime(row.get("to_date"), errors='coerce') #type:ignore
            if pd.isna(to_date):
                to_date = None
            
            collection_date = pd.to_datetime(row.get("collection_date"), errors='coerce') #type:ignore
            if pd.isna(collection_date):
                collection_date = None

            status = self._scalar(row.get("status", "active")) or "active"

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
                created_revenue += 1

        if not dry_run:
            db.commit()

        return {
            "rows": len(df),
            "created_revenue": created_revenue,
            "updated_revenue": updated_revenue,
            "skipped_rows": skipped_rows,
            "expected_columns": self.EXPECTED_COLUMNS,
        }

class MasterSummary:
    def __init__(self):
        self.metadata = MetaData()

    def get_project_level_summary(
        self, 
        db: Session,
        account_name: Optional[str] = None,
        project_name: Optional[str] = None,
        project_status: Optional[str] = None,
        project_type: Optional[str] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
        delivery_unit_name: Optional[str] = None
    ) -> List[ProjectSummary]:
        """
        Get project level summary with aggregated revenue data.
        Each project appears ONCE with all its revenue aggregated.
        """
        P = Project
        A = Account
        D = DeliveryUnit
        R = RevenueMaster
        
        project_filters = []
        revenue_join_conditions = [P.id == R.project_id]

        if account_name:
            project_filters.append(A.name.ilike(f"%{account_name}%"))

        if project_name:
            project_filters.append(P.name.ilike(f"%{project_name}%"))

        if project_status:
            project_filters.append(P.status == project_status)

        if project_type:
            project_filters.append(P.project_type == project_type)

        if delivery_unit_name:
            project_filters.append(D.name.ilike(f"%{delivery_unit_name}%"))

        # FIXED: Month/year filters should be applied to PROJECT from_date, not revenue collection_date
        # This ensures when users select July, they see projects that started in July
        if month:
            project_filters.append(func.extract('month', P.from_date) == month)

        if year:
            project_filters.append(func.extract('year', P.from_date) == year)

        project_filters_condition = and_(*project_filters) if project_filters else True

        try:
            project_level_summary = (
                db.query(
                    P.id.label("project_id"),
                    P.name.label("project_name"),
                    P.account_id,
                    A.name.label("account_name"),
                    D.name.label("delivery_unit_name"),
                    func.coalesce(func.sum(R.expected_revenue), 0).label("total_expected_rev"),
                    func.coalesce(func.sum(R.ytd_revenue), 0).label("total_ytd_rev"),
                    func.coalesce(func.sum(R.ai_direct_revenue), 0).label("total_ai_rev"),
                    func.coalesce(func.sum(R.ai_assisted_revenue), 0).label("total_ai_assist_rev"),
                    func.coalesce(func.sum(R.total_revenue), 0).label("total_revenue"),
                    func.coalesce(func.max(R.ai_direct_people), 0).label("ai_direct_people"),
                    func.coalesce(P.ai_direct_hours, 0).label("total_ai_direct_hours"),
                    func.coalesce(P.ai_assist_hours, 0).label("total_ai_assist_hours"),
                    func.extract('month', P.from_date).label("month"),
                    func.extract('year', P.from_date).label("year"),
                    P.status.label("project_status"),
                    P.project_type.label("project_type"),
                    P.from_date,
                    P.to_date,
                )
                .outerjoin(A, P.account_id == A.id)
                .outerjoin(D, A.delivery_unit_id == D.id)
                .outerjoin(R, and_(*revenue_join_conditions))  # Apply month/year filter in JOIN
                .filter(project_filters_condition)  # type:ignore
                .group_by(
                    P.id,
                    P.name,
                    P.account_id,
                    A.name,
                    D.name,
                    P.ai_direct_hours,
                    P.ai_assist_hours,
                    P.status,
                    P.project_type,
                    P.from_date,
                    P.to_date
                )
                .order_by(P.created_at.desc())
            )

            project_level_summary = project_level_summary.all()

            response = []
            for row in project_level_summary:
                try:
                    total_expected_rev = self._safe_float(row.total_expected_rev)
                    total_ytd_rev = self._safe_float(row.total_ytd_rev)
                    total_ai_rev = self._safe_float(row.total_ai_rev)
                    total_ai_assist_rev = self._safe_float(row.total_ai_assist_rev)
                    total_ai_direct_hours = self._safe_float(row.total_ai_direct_hours)
                    total_ai_assist_hours = self._safe_float(row.total_ai_assist_hours)
                    ai_direct_people = self._safe_int(row.ai_direct_people)
                    total_revenue = self._safe_float(row.total_revenue)
                    month = self._safe_int(row.month)
                    year = self._safe_int(row.year)

                    summary = ProjectSummary(
                        project_id=row.project_id,
                        project_name=row.project_name or "",
                        account_id=row.account_id,
                        account_name=row.account_name or "",
                        delivery_unit_name=row.delivery_unit_name or "",
                        total_ai_direct_hours=total_ai_direct_hours,
                        total_ai_assist_hours=total_ai_assist_hours,
                        ai_direct_people=ai_direct_people,
                        project_status=row.project_status or "active",
                        project_type=row.project_type or "",
                        from_date=row.from_date,
                        to_date=row.to_date,
                        total_expected_rev=total_expected_rev,
                        total_ytd_rev=total_ytd_rev,
                        total_ai_rev=total_ai_rev,
                        total_ai_assist_rev=total_ai_assist_rev,
                        total_revenue=total_revenue,
                        total_project_count=1,
                        month=month,
                        year=year,
                    )
                    response.append(summary)
                except Exception as e:
                    print(f"Error converting row: {e}")
                    continue

            return response
        except Exception as e:
            print(f"Error in get_project_level_summary: {str(e)}")
            raise ValueError(f"Failed to fetch project summary: {str(e)}")

    def get_dashboard_statistics(
        self,
        db: Session,
        account_name: Optional[str] = None,
        project_name: Optional[str] = None,
        project_status: Optional[str] = None,
        project_type: Optional[str] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
        delivery_unit_name: Optional[str] = None
    ) -> DashboardStatsOut:
        """Get comprehensive dashboard statistics."""
        P = Project
        A = Account
        R = RevenueMaster
        D = DeliveryUnit

        filters = []
        if account_name:
            filters.append(A.name.ilike(f"%{account_name}%"))
        if project_name:
            filters.append(P.name.ilike(f"%{project_name}%"))
        if project_status:
            filters.append(P.status == project_status)
        if project_type:
            filters.append(P.project_type == project_type)
        if month:
            filters.append(func.extract('month', P.from_date) == month)
        if year:
            filters.append(func.extract('year', P.from_date) == year)
        if delivery_unit_name:
            filters.append(D.name.ilike(f"%{delivery_unit_name}%"))

        base_query = (
            db.query(P)
            .outerjoin(A, P.account_id == A.id)
            .outerjoin(D, A.delivery_unit_id == D.id)
            .filter(and_(*filters) if filters else True)  # type:ignore
        )

        total_projects = base_query.distinct().count()
        log.log_info(f"Total Projects:- {total_projects}")
        active_projects = base_query.filter(P.status.ilike("active")).distinct().count()
        non_active_projects = total_projects - active_projects

        revenue_query = (
            db.query(R)
            .join(P, R.project_id == P.id)
            .outerjoin(A, P.account_id == A.id)
            .outerjoin(D, A.delivery_unit_id == D.id)
            .filter(and_(*filters) if filters else True)  # type:ignore
        )

        total_accounts = db.query(Account).count()
        active_accounts = total_accounts
        inactive_accounts = 0

        total_revenue = self._safe_float(
            revenue_query.with_entities(func.sum(R.total_revenue)).scalar()
        )
        
        active_revenue = self._safe_float(
            revenue_query
            .filter(P.status.ilike("active"))
            .with_entities(func.sum(R.total_revenue))
            .scalar()
        )
        
        non_active_revenue = total_revenue - active_revenue
        
        total_ai_assisted_revenue = self._safe_float(
            revenue_query.with_entities(func.sum(R.ai_assisted_revenue)).scalar()
        )
        
        total_ai_direct_revenue = self._safe_float(
            revenue_query.with_entities(func.sum(R.ai_direct_revenue)).scalar()
        )

        project_bifurcation_raw = (
            base_query.with_entities(
                P.project_type, 
                func.count(func.distinct(P.id))  # Count distinct project IDs
            )
            .group_by(P.project_type)
            .all()
        )
        project_bifurcation = [
            {"type": p_type or "Unknown", "count": count}
            for p_type, count in project_bifurcation_raw
            if p_type
        ]

        projects = self.get_project_level_summary(
            db, account_name, project_name, project_status, 
            project_type, month, year
        )

        return DashboardStatsOut(
            total_accounts=total_accounts,
            active_accounts=active_accounts,
            inactive_accounts=inactive_accounts,
            total_projects=total_projects,
            active_projects=active_projects,
            non_active_projects=non_active_projects,
            total_revenue=total_revenue,
            active_revenue=active_revenue,
            non_active_revenue=non_active_revenue,
            total_ai_assisted_revenue=total_ai_assisted_revenue,
            total_ai_direct_revenue=total_ai_direct_revenue,
            project_bifurcation=project_bifurcation,
            projects=projects,
        )

    def _safe_float(self, value) -> float:
        """Safely convert value to float, handling None and NaN."""
        import math
        if value is None:
            return 0.0
        try:
            float_val = float(value)
            if math.isnan(float_val):
                return 0.0
            return float_val
        except (TypeError, ValueError):
            return 0.0

    def _safe_int(self, value) -> Optional[int]:
        """Safely convert value to int, handling None."""
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None



# Testing Area ----------------------------------------------------------------------------------------------

# summary = MasterSummary()
# db = SessionLocal()
# response = summary.get_project_level_summary(db)
# print(response)

# importer = ImportProjectData()
# db = SessionLocal()
# fname = "backend/data_processor/migration/projects.csv"
# with open(fname, 'rb') as f:
#     file_content = f.read()

# result = importer.import_projects_from_file(
#     db=db, 
#     content=file_content, 
#     filename="projects.xlsx",
#     dry_run=False
# )

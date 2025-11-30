import io
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_
from typing import Dict, Any, Optional, List
from backend.ai_engine.tools.app_logger import Logger
log = Logger()
from backend.app.services.project import create_project
from backend.app.models.account import Account
from backend.app.models.project import Project
from backend.app.models.delivery_unit import DeliveryUnit
from backend.app.schemas.project import ProjectSummary
from backend.app.schemas.dashboard import DashboardStatsOut
from backend.app.db.session import get_db, SessionLocal
from uuid import UUID as _UUID
import pandas as pd
from sqlalchemy import MetaData, Table, select, insert


class ImportAccountsData:
    def __init__(self) -> None:
        self. EXPECTED_COLUMNS = [
                "account_name",
                "delivery_unit_id",
                "account_manager",
                "customer_overview",
                "ai_recommendations",
                "project_name",
                "status",
                "project_type",
                "expected_revenue",
                "ytd_revenue",
                "ai_direct_people",
                "ai_assisted_people",
                "ai_direct_revenue",
                "ai_assisted_revenue",
                "code_coverage_pct",
                "total_revenue",
                "project_overview",
            ]

    def _scalar(self, value):
        """Return a clean scalar string/number from potentially messy cell values.
        Handles pandas Series/NaN and lists; returns first non-null trimmed string when possible.
        """
        if isinstance(value, pd.Series):
            # take first non-null
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
    from backend.app.schemas.project import ProjectCreate

    def _get_or_create_account(self, db: Session, row: Dict[str, Any]) -> Account:
        name = self._scalar(row.get("account_name", ""))
        if not name:
            raise ValueError("Missing account_name in row")

        account = db.query(Account).filter(Account.name == name).first()
        if account:
            return account

        du_id = self._scalar(row.get("delivery_unit_id"))
        du_name = self._scalar(row.get("delivery_unit_name") or row.get("department"))
        resolved_du = None

        if du_id:
            try:
                _ = _UUID(str(du_id))
                resolved_du = db.query(DeliveryUnit).filter(DeliveryUnit.id == du_id).first()
            except Exception:
                du_name = du_name or du_id

        if not resolved_du and du_name:
            resolved_du = db.query(DeliveryUnit).filter(DeliveryUnit.name == str(du_name)).first()
            if not resolved_du:
                resolved_du = DeliveryUnit(name=str(du_name))
                db.add(resolved_du)
                db.flush()

        if not resolved_du:
            raise ValueError(f"Delivery Unit not found for account '{name}'. Provide delivery_unit_id or delivery_unit_name present in DB")

        account = Account(
            name=name,
            delivery_unit_id=resolved_du.id,
            account_manager=self._scalar(row.get("account_manager")),
            customer_overview=self._scalar(row.get("customer_overview")),
            ai_recommendations=self._scalar(row.get("ai_recommendations")),
        )
        db.add(account)
        db.flush()
        return account

    def import_accounts_and_projects_from_file(self, db: Session, content: bytes, filename: str, dry_run: bool = False):

        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))

        raw_cols = [c.strip().lower().replace(" ", "_") for c in df.columns]

        alias_map: Dict[str, str] = {}
        ALIASES = {
        "account_name": ["account_name", "account", "account_n", "customer"],
        "delivery_unit_id": ["delivery_unit_id", "du_id", "delivery_unit_uuid"],
        "delivery_unit_name": ["delivery_unit", "delivery_unit_name", "department", "du", "delivery_u"],
        "account_manager": ["account_manager", "manager"],
        "ai_recommendations": ["ai_recommendations", "ai_recomm", "recommendations"],
        "project_type": ["project_type", "project_ty", "type"],
        "project_name": ["project_name", "project", "project_n", "project name"],
        "project_overview": ["project_overview", "project_o", "overview_project", "overview"],
        "customer_overview": ["customer_overview", "customer_", "overview"],
        "status": ["status"],
        "expected_revenue": ["expected_revenue", "expected_"],
        "ytd_revenue": ["ytd_revenue", "ytd_reven"],
        "ai_direct_people": ["ai_direct_people", "ai_direct_peo"],
        "ai_assisted_people": ["ai_assisted_people", "ai_assiste_peo"],
        "ai_direct_revenue": ["ai_direct_revenue", "ai_direct"],
        "ai_assisted_revenue": ["ai_assisted_revenue", "ai_assiste"],
        "code_coverage_pct": ["code_coverage_pct", "code_covera"],
        "total_revenue": ["total_revenue", "total_reven","total"],
        "start_date": ["start_date", "start date", "start"],
        "end_date": ["end_date", "end date", "end"],
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

        cols = list(df.columns)
        if cols.count("account_name") > 1 and "account_manager" not in cols:
           
            last_idx = [i for i, c in enumerate(cols) if c == "account_name"][-1]
            
            cols[last_idx] = "account_manager"
            df.columns = cols

        required_min = {"account_name", "project_name"}
        if not required_min.issubset(set(df.columns)):
            missing = required_min - set(df.columns)
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        created_accounts = 0
        created_projects = 0
        updated_accounts = 0
        updated_projects = 0

        for _, row in df.iterrows():
            account = self._get_or_create_account(db, row) 
            if account.created_at is None:
                
                created_accounts += 1
            else:
                updated_accounts += 1

            project_name = self._scalar(row.get("project_name", ""))
            if not project_name:
                
                continue

            
            existing_project = db.query(Project).filter(
                Project.name == project_name,
                Project.account_id == account.id
            ).first()

            status = self._scalar(row.get("status", "active")) or "active"
            project_type = self._scalar(row.get("project_type")) or None
            expected_revenue = float(row.get("expected_revenue", 0) or 0)
            ytd_revenue = float(row.get("ytd_revenue", 0) or 0)
            ai_direct_people = float(row.get("ai_direct_people", 0) or 0)
            ai_assisted_people = float(row.get("ai_assisted_people", 0) or 0)
            ai_revenue = float(row.get("ai_direct_revenue", 0) or 0)
            ai_assisted_revenue = float(row.get("ai_assisted_revenue", 0) or 0)
            code_coverage_pct = float(row.get("code_coverage_pct", 0) or 0)
            total_revenue = float(row.get("total_revenue", 0) or 0)
            
            from_date = pd.to_datetime(row.get("start_date"), errors='coerce')
            if pd.isna(from_date): from_date = None
            
            to_date = pd.to_datetime(row.get("end_date"), errors='coerce')
            if pd.isna(to_date): to_date = None

            if existing_project:
                if not dry_run:
                    existing_project.status = status
                    existing_project.project_type = project_type
                    existing_project.expected_revenue = expected_revenue
                    existing_project.ytd_revenue = ytd_revenue
                    existing_project.ai_direct_people = ai_direct_people
                    existing_project.ai_assisted_people = ai_assisted_people
                    existing_project.ai_revenue = ai_revenue
                    existing_project.ai_assisted_revenue = ai_assisted_revenue
                    existing_project.code_coverage_pct = code_coverage_pct
                    existing_project.total_revenue = total_revenue
                    existing_project.from_date = from_date
                    existing_project.to_date = to_date
                    existing_project.total_ai_revenue = ai_revenue + ai_assisted_revenue
                    
                    db.add(existing_project)
                updated_projects += 1
            else:
                payload = self.ProjectCreate(
                    name=project_name,
                    account_id=account.id, 
                    status=status,
                    project_type=project_type,
                    expected_revenue=expected_revenue,
                    ytd_revenue=ytd_revenue,
                    ai_direct_people=ai_direct_people,
                    ai_assisted_people=ai_assisted_people,
                    ai_revenue=ai_revenue,
                    ai_assisted_revenue=ai_assisted_revenue,
                    code_coverage_pct=code_coverage_pct,
                    total_revenue=total_revenue,
                    from_date=from_date,
                    to_date=to_date
                )

                if not dry_run:
                    create_project(db, payload)
                created_projects += 1

        if not dry_run:
            db.commit()

        return {
            "rows": len(df),
            "created_accounts": created_accounts,
            "updated_accounts": updated_accounts,
            "created_projects": created_projects,
            "updated_projects": updated_projects,
            "expected_columns": self.EXPECTED_COLUMNS,
        }

# class ImportSOW:

class MasterSummary:
    def __init__(self):
        self.metadata = MetaData()

    def get_project_level_summary(self, 
        db: Session ,
        account_name: Optional[str] = None,
        project_name: Optional[str] = None,
        project_status: Optional[str] = None,
        project_type: Optional[str] = None,
        month: Optional[int] = None,
        year: Optional[int] = None
        ) -> List[ProjectSummary]:
        P = Project
        A = Account
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

        filters = and_(*filters) if filters else True

        project_level_summary = (
            db.query(
                P.id.label("project_id"),
                P.name.label("project_name"),
                P.account_id,
                A.name.label("account_name"),
                D.name.label("delivery_unit_name"),
                P.expected_revenue.label("total_expected_rev"),
                P.ytd_revenue.label("total_ytd_rev"),
                P.ai_revenue.label("total_ai_rev"),
                P.ai_assisted_revenue.label("total_ai_assist_rev"),
                P.ai_direct_hours.label("total_ai_direct_hours"),
                P.ai_assist_hours.label("total_ai_assist_hours"),
                case((P.status == project_status, 1), else_=0).label("total_project_count"), # This should be 1 for each project
                func.extract('month', P.from_date).label("month"),
                func.extract('year', P.from_date).label("year"),
                P.total_revenue.label("total_revenue"),
                P.status.label("project_status"),
                P.project_type.label("project_type"),
            )
            .outerjoin(A, P.account_id == A.id)
            .outerjoin(D, A.delivery_unit_id == D.id)
            .filter(filters)
        )

        project_level_summary = project_level_summary.all()

        response = [
            ProjectSummary(
                project_id=row.project_id,
                project_name=row.project_name,
                account_id=row.account_id,
                account_name=row.account_name,
                delivery_unit_name=row.delivery_unit_name,
                total_expected_rev=row.total_expected_rev or 0,
                total_ytd_rev=row.total_ytd_rev or 0,
                total_ai_rev=row.total_ai_rev or 0,
                total_ai_assist_rev=row.total_ai_assist_rev or 0,
                total_ai_direct_hours=row.total_ai_direct_hours or 0,
                total_ai_assist_hours=row.total_ai_assist_hours or 0,
                total_project_count=1, 
                month=int(row.month) if row.month else None,
                year=int(row.year) if row.year else None,
                total_revenue=row.total_revenue or 0,
                project_status=row.project_status,
                project_type=row.project_type,
            )
            for row in project_level_summary
        ]
        return response

    def get_dashboard_statistics(self,
        db: Session,
        account_name: Optional[str] = None,
        project_name: Optional[str] = None,
        project_status: Optional[str] = None,
        project_type: Optional[str] = None,
        month: Optional[int] = None,
        year: Optional[int] = None
    ) -> DashboardStatsOut:
        P = Project
        A = Account

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

        base_query = db.query(P).outerjoin(A, P.account_id == A.id).filter(and_(*filters) if filters else True)

        total_accounts = db.query(Account).count()
        # active_accounts = db.query(Account).filter(Account.is_active == True).count()
        active_accounts = total_accounts
        inactive_accounts = 0 
        total_projects = base_query.count()
        active_projects = base_query.filter(P.status.ilike("active")).count()
        non_active_projects = total_projects - active_projects
        total_revenue = base_query.with_entities(func.sum(P.total_revenue)).scalar() or 0
        active_revenue = base_query.filter(P.status.ilike("active")).with_entities(func.sum(P.total_revenue)).scalar() or 0
        non_active_revenue = total_revenue - active_revenue
        total_ai_assisted_revenue = base_query.with_entities(func.sum(P.ai_assisted_revenue)).scalar() or 0
        total_ai_direct_revenue = base_query.with_entities(func.sum(P.ai_revenue)).scalar() or 0

        project_bifurcation_raw = (
            base_query.with_entities(P.project_type, func.count(P.id))
            .group_by(P.project_type)
            .all()
        )
        project_bifurcation = [
            {"type": p_type, "count": count}
            for p_type, count in project_bifurcation_raw
            if p_type
        ]

        projects = self.get_detailed_project_summary(db, account_name, project_name, project_status, project_type, month, year)

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


# summary = MasterSummary()
# db = SessionLocal()
# response = summary.get_project_level_summary(db)
# print(response)

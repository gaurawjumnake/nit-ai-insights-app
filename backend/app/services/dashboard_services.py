import io
import pandas as pd
from datetime import datetime, date
from sqlalchemy import MetaData, Table, select, insert
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_, or_
from typing import Dict, Any, Optional, List, Union
from backend.doc_insighter.tools.app_logger import Logger
log = Logger()
from backend.app.models.account import Account
from backend.app.models.project import Project
from backend.app.models.delivery_unit import DeliveryUnit
from backend.app.models.revenue import RevenueMaster
from backend.app.schemas.project import ProjectSummary
from backend.app.schemas.dashboard import DashboardStatsOut


class MasterSummary:
    def __init__(self):
        self.metadata = MetaData()

    def get_project_level_summary_old(
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
        P = Project
        A = Account
        D = DeliveryUnit
        R = RevenueMaster
        
        project_filters = []
        revenue_filters = []

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

        if month:
            revenue_filters.append(func.extract('month', R.collection_date) == month)

        if year:
            revenue_filters.append(func.extract('year', R.collection_date) == year)

        project_filters_condition = and_(*project_filters) if project_filters else True
        
        # Build revenue join conditions
        revenue_join_conditions = [P.id == R.project_id]
        if revenue_filters:
            revenue_join_conditions.extend(revenue_filters)

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
                    # func.extract('month', R.collection_date).label("month"),
                    # func.extract('year', R.collection_date).label("year"),
                    P.status.label("project_status"),
                    P.project_type.label("project_type"),
                    P.from_date,
                    P.to_date,
                )
                .outerjoin(A, P.account_id == A.id)
                .outerjoin(D, A.delivery_unit_id == D.id)
                .outerjoin(R, and_(*revenue_join_conditions)) 
                .filter(project_filters_condition)  # type:ignore
                .group_by(
                    P.id,
                    P.name,
                    P.account_id,
                    A.name,
                    D.name,
                    # P.ai_direct_hours,
                    # P.ai_assist_hours,
                    P.status,
                    P.project_type,
                    # R.collection_date
                    # P.from_date,
                    # P.to_date
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
                    # month = self._safe_int(row.month)
                    # year = self._safe_int(row.year)

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

    def parse_date(self, date_input: Union[str, datetime, date]) -> datetime:
        if isinstance(date_input, str):
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y']:
                try:
                    return datetime.strptime(date_input, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Could not parse date string: {date_input}")
        elif isinstance(date_input, date) and not isinstance(date_input, datetime):
            return datetime.combine(date_input, datetime.min.time())
        elif isinstance(date_input, datetime):
            return date_input
        else:
            raise ValueError(f"Invalid date type: {type(date_input)}")

    def get_project_level_summary(
        self, 
        db: Session,
        account_name: Optional[str] = None,
        project_name: Optional[str] = None,
        project_status: Optional[str] = None,
        project_type: Optional[str] = None,
        start_date: Optional[Union[str, datetime, date]] = None,
        end_date: Optional[Union[str, datetime, date]] = None,
        delivery_unit_name: Optional[str] = None
    ) -> List[ProjectSummary]:
        """Get project level summary with optional filters."""
        
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

        if start_date:
            parsed_start = self.parse_date(start_date)
            revenue_join_conditions.append(R.collection_date >= parsed_start)
        if end_date:
            parsed_end = self.parse_date(end_date)
            revenue_join_conditions.append(R.collection_date <= parsed_end)

        try:
            results = (
                db.query(
                    P.id.label("project_id"),
                    P.name.label("project_name"),
                    P.account_id,
                    A.name.label("account_name"),
                    D.name.label("delivery_unit_name"),
                    P.status.label("project_status"),
                    P.project_type.label("project_type"),
                    P.from_date,
                    P.to_date,
                    P.ai_direct_hours.label("total_ai_direct_hours"),
                    P.ai_assist_hours.label("total_ai_assist_hours"),

                    func.coalesce(func.sum(R.expected_revenue), 0).label("total_expected_rev"),
                    func.coalesce(func.sum(R.ytd_revenue), 0).label("total_ytd_rev"),
                    func.coalesce(func.sum(R.ai_direct_revenue), 0).label("total_ai_rev"),
                    func.coalesce(func.sum(R.ai_assisted_revenue), 0).label("total_ai_assist_rev"),
                    func.coalesce(func.sum(R.total_revenue), 0).label("total_revenue"),
                    func.coalesce(func.max(R.ai_direct_people), 0).label("ai_direct_people"),

                    func.min(R.collection_date).label("min_date"),
                    func.max(R.collection_date).label("max_date"),
                )
                .join(A, P.account_id == A.id)
                .join(D, A.delivery_unit_id == D.id)
                .outerjoin(R, and_(*revenue_join_conditions))
                .filter(and_(*project_filters) if project_filters else True) # type:ignore
                .group_by(P.id, P.name, P.account_id, A.name, D.name, P.status, 
                        P.project_type, P.from_date, P.to_date, P.ai_direct_hours, 
                        P.ai_assist_hours)
                .order_by(P.created_at.desc())
                .all()
            )

            response = []
            for row in results:
                month = row.min_date.month if row.min_date else None
                year = row.min_date.year if row.min_date else None
                
                summary = ProjectSummary(
                    project_id=row.project_id,
                    project_name=row.project_name or "",
                    account_id=row.account_id,
                    account_name=row.account_name or "",
                    delivery_unit_name=row.delivery_unit_name or "",
                    project_status=row.project_status or "active",
                    project_type=row.project_type or "",
                    from_date=row.from_date,
                    to_date=row.to_date,
                    total_ai_direct_hours=self._safe_float(row.total_ai_direct_hours),
                    total_ai_assist_hours=self._safe_float(row.total_ai_assist_hours),
                    ai_direct_people=self._safe_int(row.ai_direct_people),
                    total_expected_rev=self._safe_float(row.total_expected_rev),
                    total_ytd_rev=self._safe_float(row.total_ytd_rev),
                    total_ai_rev=self._safe_float(row.total_ai_rev),
                    total_ai_assist_rev=self._safe_float(row.total_ai_assist_rev),
                    total_revenue=self._safe_float(row.total_revenue),
                    total_project_count=1,
                    # month=month,
                    # year=year,
                )
                response.append(summary)

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
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
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

        # if month:
        #     filters.append(func.extract('month', P.from_date) == month)
        # if year:
        #     filters.append(func.extract('year', P.from_date) == year)

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
            project_type, start_date, end_date
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

# # # for testing ------------------------------------------
# ms = MasterSummary()
# from backend.app.db.session import SessionLocal
# project_id ="561a6d34-08d4-4368-b203-1a5cc1e00d10"
# acct = ""
# p_name = ""
# p_status = ""
# p_type = ""
# start_date = datetime.strptime("2025-07-01", "%Y-%m-%d").date()
# end_date = datetime.strptime("2025-08-01", "%Y-%m-%d").date()
# du = ""
# session = SessionLocal()

# summary = ms.get_project_level_summary(session,
#                                        start_date=start_date,
#                                        end_date=end_date
#                                        )

# print(summary)
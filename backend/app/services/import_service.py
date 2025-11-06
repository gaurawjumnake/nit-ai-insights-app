import io
import pandas as pd
from sqlalchemy.orm import Session
from typing import Dict, Any

from .project import create_project
from ..models.account import Account
from ..models.delivery_unit import DeliveryUnit
from uuid import UUID as _UUID
import pandas as pd
def _scalar(value):
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
from ..schemas.project import ProjectCreate


EXPECTED_COLUMNS = [
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
]


def _get_or_create_account(db: Session, row: Dict[str, Any]) -> Account:
    name = _scalar(row.get("account_name", ""))
    if not name:
        raise ValueError("Missing account_name in row")

    account = db.query(Account).filter(Account.name == name).first()
    if account:
        return account

    du_id = _scalar(row.get("delivery_unit_id"))
    du_name = _scalar(row.get("delivery_unit_name") or row.get("department"))
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
        account_manager=_scalar(row.get("account_manager")),
        customer_overview=_scalar(row.get("customer_overview")),
        ai_recommendations=_scalar(row.get("ai_recommendations")),
    )
    db.add(account)
    db.flush()
    return account


def import_accounts_and_projects_from_file(db: Session, content: bytes, filename: str, dry_run: bool = False):

    if filename.lower().endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content))
    else:
        df = pd.read_excel(io.BytesIO(content))

    raw_cols = [c.strip().lower().replace(" ", "_") for c in df.columns]

    alias_map: Dict[str, str] = {}
    ALIASES = {
        "account_name": ["account_name", "account", "customer", "customer_name", "account_n"],
        "delivery_unit_id": ["delivery_unit_id", "du_id", "delivery_unit_uuid"],
        "delivery_unit_name": ["delivery_unit", "delivery_unit_name", "department", "du", "delivery_u"],
        "account_manager": ["account_manager", "manager"],
        "customer_overview": ["customer_overview", "customer_", "overview"],
        "ai_recommendations": ["ai_recommendations", "ai_recomm", "recommendations"],
        "project_name": ["project_name", "project", "project_n", "project name"],
        "status": ["status"],
        "project_type": ["project_type", "project_ty", "type"],
        "expected_revenue": ["expected_revenue", "expected_"],
        "ytd_revenue": ["ytd_revenue", "ytd_reven"],
        "ai_direct_people": ["ai_direct_people", "ai_direct_peo"],
        "ai_assisted_people": ["ai_assisted_people", "ai_assiste_peo"],
        "ai_direct_revenue": ["ai_direct_revenue", "ai_direct"],
        "ai_assisted_revenue": ["ai_assisted_revenue", "ai_assiste"],
        "code_coverage_pct": ["code_coverage_pct", "code_covera"],
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
            canonical_cols[col] = col  # keep as-is

    # Apply rename
    rename_dict = {orig: canon for orig, canon in canonical_cols.items() if orig != canon}
    df.columns = raw_cols
    if rename_dict:
        df = df.rename(columns=rename_dict)

    # Handle duplicate canonical names (common when headers are truncated)
    # Special-case: if two columns became 'account_name', try to map the second to 'account_manager'
    cols = list(df.columns)
    if cols.count("account_name") > 1 and "account_manager" not in cols:
        # rename the last occurrence to account_manager
        last_idx = [i for i, c in enumerate(cols) if c == "account_name"][-1]
        # Build a new columns list
        cols[last_idx] = "account_manager"
        df.columns = cols

    # Validate columns subset (not all required, but at least account and project name)
    required_min = {"account_name", "project_name"}
    if not required_min.issubset(set(df.columns)):
        missing = required_min - set(df.columns)
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    created_accounts = 0
    created_projects = 0
    updated_accounts = 0

    for _, row in df.iterrows():
        account = _get_or_create_account(db, row)
        if account.created_at is None:
            # If Account model has created_at; if not, approximate
            created_accounts += 1
        else:
            updated_accounts += 1

        project_name = _scalar(row.get("project_name", ""))
        if not project_name:
            # Skip if no project in row
            continue

        # Build ProjectCreate
        payload = ProjectCreate(
            name=project_name,
            account_id=account.id,
            status=_scalar(row.get("status", "active")) or "active",
            project_type=_scalar(row.get("project_type")) or None,
            expected_revenue=float(row.get("expected_revenue", 0) or 0),
            ytd_revenue=float(row.get("ytd_revenue", 0) or 0),
            ai_direct_people=float(row.get("ai_direct_people", 0) or 0),
            ai_assisted_people=float(row.get("ai_assisted_people", 0) or 0),
            ai_revenue=float(row.get("ai_direct_revenue", 0) or 0),
            ai_assisted_revenue=float(row.get("ai_assisted_revenue", 0) or 0),
            code_coverage_pct=float(row.get("code_coverage_pct", 0) or 0),
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
        "expected_columns": EXPECTED_COLUMNS,
    }



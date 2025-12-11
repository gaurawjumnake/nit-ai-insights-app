
from typing import Dict, Any, Optional, List
import pandas as pd

   
def safe_float(value, default=0.0):
    """Convert value to float, handling NaN, None, and empty strings."""
    if pd.isna(value) or value is None or str(value).strip() == "":
        return default
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return default


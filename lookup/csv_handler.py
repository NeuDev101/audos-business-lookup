from __future__ import annotations

import io
from typing import Dict, List

import pandas as pd

from lookup.japan import lookup_japan


def process_csv(file_bytes: bytes) -> List[Dict[str, str]]:
    if not file_bytes:
        return []

    buffer = io.BytesIO(file_bytes)
    try:
        df = pd.read_csv(buffer, dtype=str).fillna("")
    except Exception:
        return []

    id_column = None
    for candidate in ("business_id", "corporate_number"):
        if candidate in df.columns:
            id_column = candidate
            break

    if not id_column:
        return []

    results: List[Dict[str, str]] = []

    for _, row in df.iterrows():
        business_id = (row.get(id_column) or "").strip()
        if not business_id:
            continue
        try:
            lookup_result = lookup_japan(business_id)
        except Exception:
            lookup_result = {"error": "Lookup failed", "business_id": business_id}

        if "error" in lookup_result:
            if "business_id" not in lookup_result:
                lookup_result["business_id"] = business_id
        results.append(lookup_result)

    return results




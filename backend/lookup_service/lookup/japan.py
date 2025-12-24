import os
from typing import Any, Dict, List

import requests


API_BASE_URL = "https://api.houjin-bangou.nta.go.jp/4/num"


def _build_address(record: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in (
        "prefectureName",
        "prefecture_name",
        "cityName",
        "city_name",
        "streetNumber",
        "street_number",
        "addressDetail",
        "address_detail",
        "addressOutside",
        "address_outside",
    ):
        value = record.get(key)
        if value:
            parts.append(value)
    return " ".join(parts)


def lookup_japan(business_id: str) -> dict:
    if not business_id:
        return {"error": "Not found"}

    params: Dict[str, str] = {
        "number": business_id,
        "type": "12",  # JSON response
    }

    api_key = os.getenv("NTA_API_KEY") or os.getenv("HOUJIN_BANGOU_API_KEY")
    if api_key:
        params["key"] = api_key

    try:
        response = requests.get(API_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return {"error": "Not found"}

    try:
        data = response.json()
    except ValueError:
        return {"error": "Not found"}

    records = data.get("list") or data.get("corporations") or []
    if not records:
        return {"error": "Not found"}

    record = records[0]
    corp_number = record.get("corporateNumber") or record.get("corporate_number")
    company_name = record.get("name") or record.get("nameImageId")
    address = _build_address(record)

    if not corp_number or not company_name:
        return {"error": "Not found"}

    return {
        "business_id": corp_number,
        "company_name": company_name,
        "address": address or None,
    }


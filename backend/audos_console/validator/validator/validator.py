import json
import os
try:
    import regex as re  # Supports Unicode properties when available
except ImportError:  # Fallback when regex isn't installed
    import re
from datetime import datetime
from typing import Any, Dict, List


class InvoiceValidator:
    """Validator for per-field and full-invoice checks using rules.json."""

    def __init__(self) -> None:
        base_dir = os.path.dirname(__file__)
        rules_path = os.path.join(base_dir, "rules.json")

        with open(rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        rules = data.get("rules")
        if not isinstance(rules, list):
            raise ValueError("rules.json must contain 'rules': [ ... ]")

        self.rules: List[Dict[str, Any]] = rules

    # ====================================================
    # SINGLE-FIELD VALIDATION (LIVE GREEN/RED CHECKMARKS)
    # ====================================================

    def validate_field_only(self, field_name: str, field_value: Any) -> Dict[str, str]:
        """
        Validate a single field for live validation.
        This does NOT run full invoice logic.
        """

        matched_any = False

        for rule in self.rules:
            rule_field = rule.get("field")
            if not isinstance(rule_field, str):
                continue

            rtype = rule.get("type")

            # Match exact rules like "issuer_id"
            if rule_field == field_name:
                matched_any = True

            # Match nested item rules like "items[].tax_rate"
            elif "[]" in rule_field and rule_field.endswith("." + field_name):
                matched_any = True

            else:
                continue

            # ----------------------------------------------------
            # Apply rule
            # ----------------------------------------------------

            # Required
            if rtype == "required":
                if field_value in ("", None, [], {}):
                    return {"status": "fail"}

            # Regex pattern
            elif rtype == "regex":
                pattern = rule.get("pattern")
                if pattern:
                    if not re.match(pattern, str(field_value or "")):
                        return {"status": "fail"}

            # Date (ISO)
            elif rtype == "date_iso":
                try:
                    datetime.fromisoformat(str(field_value))
                except Exception:
                    return {"status": "fail"}

            # Enum allowed (tax rates)
            elif rtype == "enum_any_item":
                allowed = [str(a) for a in rule.get("allowed", [])]
                if str(field_value) not in allowed:
                    return {"status": "fail"}

            # Other rule types ignored in live mode

        # No matching rules → treat field as valid in live mode
        if not matched_any:
            return {"status": "pass"}

        return {"status": "pass"}

    # ====================================================
    # FULL-INVOICE VALIDATION (FOR PDF STAMP)
    # ====================================================

    def validate(self, invoice: Dict[str, Any], language: str = "both", auto_fixed: List[str] = None) -> Dict[str, Any]:
        """
        Validates full invoice for PDF generation.
        
        Args:
            invoice: Invoice data dictionary
            language: Language for messages ("both", "ja", "en")
            auto_fixed: Optional list of auto-fix descriptions (e.g., ["date formatted", "phone converted"])
        """

        fields: Dict[str, Any] = {}
        issues_count = 0
        needs_user_action: List[str] = []
        
        if auto_fixed is None:
            auto_fixed = []

        def mark_fail(field: str, ja: str, en: str) -> None:
            nonlocal issues_count, needs_user_action
            if field not in fields:
                fields[field] = {
                    "status": "fail",
                    "messages": {"ja": [ja], "en": [en]},
                }
            else:
                fields[field]["status"] = "fail"
                fields[field]["messages"]["ja"].append(ja)
                fields[field]["messages"]["en"].append(en)
            issues_count += 1
            
            # Track fields that need user action
            if field not in needs_user_action:
                needs_user_action.append(field)

        for rule in self.rules:
            rule_field = rule.get("field")
            rtype = rule.get("type")

            if not isinstance(rule_field, str):
                continue

            # -----------------------------
            # Required
            # -----------------------------
            if rtype == "required":
                val = invoice.get(rule_field)
                if val in ("", None, [], {}):
                    mark_fail(rule_field,
                              f"{rule_field} は必須項目です。",
                              f"{rule_field} is required.")

            # -----------------------------
            # Regex
            # -----------------------------
            elif rtype == "regex":
                val = invoice.get(rule_field)
                pattern = rule.get("pattern")
                if pattern and val not in (None, ""):
                    if not re.match(pattern, str(val)):
                        mark_fail(rule_field,
                                  f"{rule_field} の形式が正しくありません。",
                                  f"Invalid format for {rule_field}.")

            # -----------------------------
            # ISO Date
            # -----------------------------
            elif rtype == "date_iso":
                val = invoice.get(rule_field)
                if val not in (None, ""):
                    try:
                        datetime.fromisoformat(str(val))
                    except Exception:
                        mark_fail(rule_field,
                                  f"{rule_field} は YYYY-MM-DD 形式である必要があります。",
                                  f"{rule_field} must be YYYY-MM-DD.")

            # -----------------------------
            # Enum for items[].tax_rate
            # -----------------------------
            elif rtype == "enum_any_item":
                list_path, _, tail = rule_field.partition("[]")
                subfield = tail.lstrip(".")
                items = invoice.get(list_path, [])
                allowed = [str(a) for a in rule.get("allowed", [])]

                if isinstance(items, list):
                    for idx, item in enumerate(items):
                        val = str(item.get(subfield))
                        if val not in allowed:
                            fname = f"{list_path}[{idx}].{subfield}"
                            mark_fail(fname,
                                      f"{fname} の税率が許可された値ではありません。",
                                      f"{fname} tax rate is not allowed.")

            # -----------------------------
            # Ignore unsupported types in full mode
            # -----------------------------
            else:
                continue

        overall_ok = all(entry["status"] == "pass" for entry in fields.values())

        summary_ja = "適格請求書として要件を満たしています。" if overall_ok else "一部の項目に修正が必要です。"
        summary_en = "Invoice meets qualified invoice requirements." if overall_ok else "Some fields require correction."

        # Build user action messages from failed fields
        user_action_messages = []
        for field_name in needs_user_action:
            field_info = fields.get(field_name, {})
            messages = field_info.get("messages", {})
            if messages.get("en"):
                # Use the first English message, or create a descriptive one
                en_msg = messages["en"][0]
                # Format as "field_name: message" for clarity
                user_action_messages.append(f"{field_name}: {en_msg}")
            else:
                user_action_messages.append(f"{field_name} format invalid")

        return {
            "language": language,
            "overall": {
                "status": "pass" if overall_ok else "fail",
                "compliant": overall_ok,
                "summary": {
                    "ja": summary_ja,
                    "en": summary_en,
                },
            },
            "fields": fields,
            "issues_count": issues_count,
            "auto_fix_summary": {
                "auto_fixed": auto_fixed,
                "needs_user_action": user_action_messages,
            },
        }


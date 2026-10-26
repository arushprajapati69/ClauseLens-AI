"""Deterministic calculation tools for ClauseLens AI.

Principles:
- Python owns all arithmetic (dates, currencies, tiers, durations).
- The LLM never computes numbers or dates.
- Zero eval/exec: static dispatch with inspect.signature verification.
"""

from datetime import datetime
import inspect
import re
from typing import Any, Callable, Dict, List, Optional
import config

WORD_TO_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "fourteen": 14, "twenty": 20,
    "twenty-four": 24, "thirty": 30, "sixty": 60, "ninety": 90,
}


def _require_int(name: str, value: Any, lo: Optional[int] = None, hi: Optional[int] = None) -> int:
    """Strictly validates integer values, explicitly rejecting booleans and floats."""
    if type(value) is not int:
        raise TypeError(f"Argument '{name}' must be an int, got {type(value).__name__} ({value!r})")
    if lo is not None and value < lo:
        raise ValueError(f"Argument '{name}'={value} is below minimum allowed {lo}")
    if hi is not None and value > hi:
        raise ValueError(f"Argument '{name}'={value} is above maximum allowed {hi}")
    return value


def days_between(start_date: str, action_date: str) -> Dict[str, Any]:
    """Computes days of notice between an action date (e.g., cancellation) and a start date (e.g., check-in).
    
    Format: ISO YYYY-MM-DD.
    Returns: {"days_notice": int}
    """
    if not isinstance(start_date, str) or not isinstance(action_date, str):
        raise TypeError("start_date and action_date must be ISO date strings (YYYY-MM-DD)")
    
    try:
        dt_start = datetime.strptime(start_date.strip(), "%Y-%m-%d").date()
        dt_action = datetime.strptime(action_date.strip(), "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"Invalid date format, expected YYYY-MM-DD: {e}")

    delta = (dt_start - dt_action).days
    if delta < 0:
        raise ValueError(f"action_date ({action_date}) cannot be after start_date ({start_date})")
    
    return {"days_notice": delta}


def apply_refund_tiers(
    days_notice: int,
    amount_paid: int,
    tiers: List[Dict[str, Any]],
    flat_fee: int = 0,
    currency: str = config.CURRENCY
) -> Dict[str, Any]:
    """Applies policy cancellation refund tiers deterministically.
    
    Rounding rule: Integer floor division (amount_paid * refund_percent // 100).
    Returns:
        {
            "currency": str,
            "days_notice": int,
            "refund_percent": int,
            "refund_amount": int,
            "deducted_fee": int
        }
    """
    _require_int("days_notice", days_notice, lo=0, hi=10000)
    _require_int("amount_paid", amount_paid, lo=0, hi=100000000)
    _require_int("flat_fee", flat_fee, lo=0, hi=amount_paid)

    if not isinstance(tiers, list) or len(tiers) == 0:
        raise ValueError("tiers must be a non-empty list of tier definitions")

    seen_days = set()
    cleaned_tiers = []
    for idx, t in enumerate(tiers):
        if not isinstance(t, dict):
            raise TypeError(f"Tier #{idx} must be a dictionary")
        if "min_days_notice" not in t or "refund_percent" not in t:
            raise ValueError(f"Tier #{idx} missing required keys 'min_days_notice' or 'refund_percent'")
        
        min_days = _require_int(f"tier[{idx}].min_days_notice", t["min_days_notice"], lo=0, hi=10000)
        pct = _require_int(f"tier[{idx}].refund_percent", t["refund_percent"], lo=0, hi=100)

        if min_days in seen_days:
            raise ValueError(f"Duplicate min_days_notice={min_days} in refund tiers")
        seen_days.add(min_days)
        cleaned_tiers.append({"min_days_notice": min_days, "refund_percent": pct})

    # Sort descending by min_days_notice to find the qualifying threshold
    cleaned_tiers.sort(key=lambda x: x["min_days_notice"], reverse=True)

    matched_tier = None
    for t in cleaned_tiers:
        if days_notice >= t["min_days_notice"]:
            matched_tier = t
            break

    if matched_tier is None:
        refund_percent = 0
    else:
        refund_percent = matched_tier["refund_percent"]

    gross_refund = (amount_paid * refund_percent) // 100
    actual_fee = min(gross_refund, flat_fee) if refund_percent > 0 else 0
    net_refund = max(0, gross_refund - flat_fee if refund_percent > 0 else 0)

    return {
        "currency": currency,
        "days_notice": days_notice,
        "refund_percent": refund_percent,
        "gross_refund": gross_refund,
        "refund_amount": net_refund,
        "deducted_fee": flat_fee if refund_percent > 0 else 0
    }


def extract_numeric_facts(text: str) -> List[Dict[str, Any]]:
    """Extracts numeric facts, currencies, durations, and percentages from text.
    
    Normalises durations to standard units (days or hours) for comparison.
    """
    facts: List[Dict[str, Any]] = []
    if not text:
        return facts

    # 1. Money patterns: ₹250, Rs. 499, INR 12,000, 250 rupees
    money_pat = re.compile(
        r"(?:₹|Rs\.?|INR)\s*([0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)",
        re.IGNORECASE
    )
    for m in money_pat.finditer(text):
        val = int(m.group(1).replace(",", ""))
        facts.append({
            "type": "money",
            "raw": m.group(0).strip(),
            "value": val,
            "unit": "INR"
        })

    # 2. Percentage patterns: 50%, 100 percent
    pct_pat = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*(?:%|percent)", re.IGNORECASE)
    for m in pct_pat.finditer(text):
        val = float(m.group(1))
        facts.append({
            "type": "percentage",
            "raw": m.group(0).strip(),
            "value": int(val) if val.is_integer() else val,
            "unit": "%"
        })

    # 3. Durations with written numbers or digits, e.g. "seven (7) days", "7 or more days", "3 to 6 days", "24 hours", "1 year"
    # Handles "7 or more days", "3 to 6 days", "7-day"
    dur_pat = re.compile(
        r"\b(?:([a-z]+)\s*(?:\(([0-9]+)\)\s*)?|([0-9]+))\s*"
        r"(?:(?:to|-)\s*(?:[a-z]+|[0-9]+)\s*|\s*or\s*(?:more|fewer|less)\s*)?"
        r"(days?|business days?|working days?|hours?|weeks?|months?|years?)\b",
        re.IGNORECASE
    )
    for m in dur_pat.finditer(text):
        word_num = m.group(1)
        parens_num = m.group(2)
        digit_num = m.group(3)
        unit = m.group(4).lower()

        val = None
        if parens_num:
            val = int(parens_num)
        elif digit_num:
            val = int(digit_num)
        elif word_num and word_num.lower() in WORD_TO_NUM:
            val = WORD_TO_NUM[word_num.lower()]

        if val is None:
            continue

        # Normalization
        norm_unit = "days"
        norm_val = val
        if "hour" in unit:
            norm_unit = "hours"
            norm_val = val
        elif "week" in unit:
            norm_unit = "days"
            norm_val = val * 7
        elif "month" in unit:
            norm_unit = "months"
            norm_val = val
        elif "year" in unit:
            norm_unit = "months"
            norm_val = val * 12

        facts.append({
            "type": "duration",
            "raw": m.group(0).strip(),
            "value": val,
            "unit": unit,
            "norm_value": norm_val,
            "norm_unit": norm_unit
        })

    # 4. Standalone plain numbers (e.g., section numbers or isolated counts)
    plain_num_pat = re.compile(r"\b([0-9]+)\b")
    for m in plain_num_pat.finditer(text):
        val = int(m.group(1))
        # Exclude if already captured in money or duration
        span = m.span()
        already = False
        for f in facts:
            if m.group(1) in f["raw"]:
                already = True
                break
        if not already:
            facts.append({
                "type": "number",
                "raw": m.group(0),
                "value": val,
                "unit": "none"
            })

    return facts


TOOLS: Dict[str, Callable[..., Any]] = {
    "days_between": days_between,
    "apply_refund_tiers": apply_refund_tiers
}


def dispatch(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Safely dispatches tool invocation through static registry and inspect.signature.
    
    Zero eval/exec. Returns {"result": ...} or {"error": str}.
    """
    if name not in TOOLS:
        return {"error": f"Unknown tool '{name}'. Available: {list(TOOLS.keys())}"}

    func = TOOLS[name]
    try:
        sig = inspect.signature(func)
        bound = sig.bind(**args)
        bound.apply_defaults()
        res = func(*bound.args, **bound.kwargs)
        return {"result": res}
    except TypeError as te:
        return {"error": f"Invalid arguments for tool '{name}': {te}"}
    except ValueError as ve:
        return {"error": f"Value error in tool '{name}': {ve}"}
    except Exception as e:
        return {"error": f"Tool execution failed: {e}"}

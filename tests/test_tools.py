import pytest
from tools import _require_int, days_between, apply_refund_tiers, extract_numeric_facts, dispatch, TOOLS

def test_require_int():
    assert _require_int("x", 10) == 10
    assert _require_int("x", 0, lo=0) == 0
    assert _require_int("x", 5, lo=0, hi=10) == 5

    # Reject booleans
    with pytest.raises(TypeError):
        _require_int("x", True)
    with pytest.raises(TypeError):
        _require_int("x", False)

    # Reject floats
    with pytest.raises(TypeError):
        _require_int("x", 5.0)

    # Reject out of bounds
    with pytest.raises(ValueError):
        _require_int("x", -1, lo=0)
    with pytest.raises(ValueError):
        _require_int("x", 11, lo=0, hi=10)


def test_days_between():
    res = days_between("2026-11-10", "2026-11-05")
    assert res == {"days_notice": 5}

    res_same = days_between("2026-11-10", "2026-11-10")
    assert res_same == {"days_notice": 0}

    # Action after start
    with pytest.raises(ValueError, match="cannot be after"):
        days_between("2026-11-05", "2026-11-10")

    # Invalid date format
    with pytest.raises(ValueError):
        days_between("10/11/2026", "2026-11-05")


def test_apply_refund_tiers_normal():
    tiers = [
        {"min_days_notice": 7, "refund_percent": 100},
        {"min_days_notice": 3, "refund_percent": 50},
        {"min_days_notice": 0, "refund_percent": 0}
    ]
    # 8 days notice -> 100% refund with flat fee of 250
    res = apply_refund_tiers(days_notice=8, amount_paid=10000, tiers=tiers, flat_fee=250)
    assert res["refund_percent"] == 100
    assert res["gross_refund"] == 10000
    assert res["refund_amount"] == 9750
    assert res["deducted_fee"] == 250

    # 5 days notice -> 50% refund with flat fee of 250
    res = apply_refund_tiers(days_notice=5, amount_paid=10000, tiers=tiers, flat_fee=250)
    assert res["refund_percent"] == 50
    assert res["gross_refund"] == 5000
    assert res["refund_amount"] == 4750

    # 1 day notice -> 0% refund
    res = apply_refund_tiers(days_notice=1, amount_paid=10000, tiers=tiers, flat_fee=250)
    assert res["refund_percent"] == 0
    assert res["refund_amount"] == 0


def test_apply_refund_tiers_validation():
    # Duplicate tier
    with pytest.raises(ValueError, match="Duplicate"):
        apply_refund_tiers(
            days_notice=5, amount_paid=1000,
            tiers=[{"min_days_notice": 3, "refund_percent": 50}, {"min_days_notice": 3, "refund_percent": 40}]
        )

    # Boolean passed as amount_paid
    with pytest.raises(TypeError):
        apply_refund_tiers(days_notice=5, amount_paid=True, tiers=[{"min_days_notice": 0, "refund_percent": 100}])


def test_extract_numeric_facts():
    text = (
        "Cancellations 7 or more days prior incur a ₹250 booking fee. "
        "Between 3 to 6 days notice gives 50% refund. Within 24 hours is non-refundable. "
        "Processed within ten (10) business days."
    )
    facts = extract_numeric_facts(text)
    
    # Check money
    money_facts = [f for f in facts if f["type"] == "money"]
    assert any(f["value"] == 250 for f in money_facts)

    # Check percentages
    pct_facts = [f for f in facts if f["type"] == "percentage"]
    assert any(f["value"] == 50 for f in pct_facts)

    # Check durations
    dur_facts = [f for f in facts if f["type"] == "duration"]
    assert any(f["value"] == 7 and f["norm_unit"] == "days" for f in dur_facts)
    assert any(f["value"] == 24 and f["norm_unit"] == "hours" for f in dur_facts)
    assert any(f["value"] == 10 and f["norm_unit"] == "days" for f in dur_facts)


def test_dispatch():
    res = dispatch("days_between", {"start_date": "2026-11-10", "action_date": "2026-11-05"})
    assert res == {"result": {"days_notice": 5}}

    # Unknown tool
    res_unknown = dispatch("non_existent_tool", {})
    assert "error" in res_unknown

    # Invalid arguments bound
    res_bad_arg = dispatch("days_between", {"wrong_param": "2026-11-10"})
    assert "error" in res_bad_arg

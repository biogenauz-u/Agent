from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app.modules.finance.exceptions import FinanceValidationError
from app.modules.finance.utils import (
    category_slug,
    format_money,
    normalize_category_name,
    normalize_currency,
    parse_amount,
    parse_transaction_date,
    period_range,
)

TZ = ZoneInfo("Asia/Tashkent")
NOW = datetime(2026, 9, 24, 20, tzinfo=UTC)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("85000", Decimal("85000.00")),
        ("85 000", Decimal("85000.00")),
        ("85,000", Decimal("85000.00")),
        ("1,250.50", Decimal("1250.50")),
        (Decimal("100.1"), Decimal("100.10")),
    ],
)
def test_amount_parsing_is_decimal(raw, expected) -> None:
    result = parse_amount(raw)
    assert result == expected and isinstance(result, Decimal)


@pytest.mark.parametrize("raw", ["0", "-1", "abc", "NaN", "Infinity", "100,50", "1e3"])
def test_invalid_amounts_rejected(raw: str) -> None:
    with pytest.raises(FinanceValidationError):
        parse_amount(raw)


def test_float_is_explicitly_rejected() -> None:
    with pytest.raises(FinanceValidationError, match="Float"):
        parse_amount(10.5)  # type: ignore[arg-type]


def test_currency_normalization_and_rejection() -> None:
    assert normalize_currency(" usd ") == "USD"
    with pytest.raises(FinanceValidationError):
        normalize_currency("GBP")


def test_money_format_is_deterministic() -> None:
    assert format_money(Decimal(85000), "UZS") == "85,000 UZS"
    assert format_money(Decimal("1250.50"), "USD") == "1,250.50 USD"
    assert format_money(Decimal(0), "EUR") == "0 EUR"


def test_category_normalization_prevents_case_variants() -> None:
    assert normalize_category_name("  Business   Income ") == "Business Income"
    assert category_slug("Taxi") == category_slug(" TAXI ") == "taxi"


def test_date_parser() -> None:
    assert parse_transaction_date("24.09.2026", TZ).isoformat() == "2026-09-24"
    with pytest.raises(FinanceValidationError):
        parse_transaction_date("2026-09-24", TZ)


def test_today_range_uses_tashkent_calendar_day() -> None:
    # 20:00 UTC is already the next day in Tashkent.
    assert tuple(item.isoformat() for item in period_range("today", NOW, TZ)) == (
        "2026-09-25",
        "2026-09-26",
    )


def test_week_starts_monday() -> None:
    assert tuple(item.isoformat() for item in period_range("week", NOW, TZ)) == (
        "2026-09-21",
        "2026-09-28",
    )


def test_month_and_year_ranges() -> None:
    assert tuple(item.isoformat() for item in period_range("month", NOW, TZ)) == (
        "2026-09-01",
        "2026-10-01",
    )
    assert tuple(item.isoformat() for item in period_range("year", NOW, TZ)) == (
        "2026-01-01",
        "2027-01-01",
    )

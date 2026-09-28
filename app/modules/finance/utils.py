import re
import unicodedata
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from app.modules.finance.exceptions import FinanceValidationError

MONEY_QUANTUM = Decimal("0.01")
MAX_AMOUNT = Decimal("999999999999999999.99")
SUPPORTED_CURRENCIES = frozenset({"UZS", "USD", "EUR"})


def parse_amount(value: str | Decimal) -> Decimal:
    if isinstance(value, float):
        raise FinanceValidationError("Float amounts are not accepted.")
    raw = str(value).strip()
    if not raw:
        raise FinanceValidationError("Amount is required.")
    if re.fullmatch(r"\d{1,3}(?:[ ,]\d{3})+(?:\.\d{1,2})?", raw):
        raw = raw.replace(" ", "").replace(",", "")
    elif not re.fullmatch(r"\d+(?:\.\d{1,2})?", raw):
        raise FinanceValidationError("Amount format is invalid.")
    try:
        amount = Decimal(raw).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        raise FinanceValidationError("Amount format is invalid.") from None
    if not amount.is_finite() or amount <= 0 or amount > MAX_AMOUNT:
        raise FinanceValidationError("Amount must be positive and within supported limits.")
    return amount


def normalize_currency(value: str) -> str:
    currency = value.strip().upper()
    if currency not in SUPPORTED_CURRENCIES:
        raise FinanceValidationError("Currency must be UZS, USD, or EUR.")
    return currency


def normalize_category_name(value: str) -> str:
    name = " ".join(unicodedata.normalize("NFKC", value).split())
    if not 1 <= len(name) <= 80 or any(ord(character) < 32 for character in name):
        raise FinanceValidationError("Category name must contain 1-80 safe characters.")
    return name


def category_slug(value: str) -> str:
    name = normalize_category_name(value).casefold()
    slug = re.sub(r"[^\w]+", "-", name, flags=re.UNICODE).strip("-_")
    if not slug:
        raise FinanceValidationError("Category name is invalid.")
    return slug[:80]


def parse_transaction_date(value: str, timezone: ZoneInfo) -> date:
    text = value.strip().casefold()
    if text == "bugun":
        return datetime.now(timezone).date()
    try:
        day, month, year = (int(part) for part in text.split("."))
        return date(year, month, day)
    except ValueError:
        raise FinanceValidationError("Date must use DD.MM.YYYY or 'bugun'.") from None


def format_money(amount: Decimal, currency: str) -> str:
    if isinstance(amount, float):
        raise FinanceValidationError("Float amounts are not accepted.")
    try:
        normalized = Decimal(amount).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        raise FinanceValidationError("Amount format is invalid.") from None
    if not normalized.is_finite() or normalized < 0:
        raise FinanceValidationError("Formatted amount must be non-negative.")
    decimals = 0 if normalized == normalized.to_integral() else 2
    return f"{normalized:,.{decimals}f} {normalize_currency(currency)}"


def period_range(kind: str, now: datetime, timezone: ZoneInfo) -> tuple[date, date]:
    local = now.astimezone(timezone).date()
    if kind == "today":
        return local, local + timedelta(days=1)
    if kind == "week":
        start = local - timedelta(days=local.weekday())
        return start, start + timedelta(days=7)
    if kind == "month":
        start = local.replace(day=1)
        end = date(start.year + int(start.month == 12), start.month % 12 + 1, 1)
        return start, end
    if kind == "year":
        return date(local.year, 1, 1), date(local.year + 1, 1, 1)
    raise FinanceValidationError("Unsupported report period.")

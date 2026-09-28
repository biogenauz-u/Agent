from app.database.models.finance import FinanceCategoryType

DEFAULT_CATEGORIES: tuple[tuple[str, str, FinanceCategoryType], ...] = (
    ("Food", "food", FinanceCategoryType.EXPENSE),
    ("Taxi", "taxi", FinanceCategoryType.EXPENSE),
    ("Transport", "transport", FinanceCategoryType.EXPENSE),
    ("Shopping", "shopping", FinanceCategoryType.EXPENSE),
    ("Business", "business", FinanceCategoryType.EXPENSE),
    ("Office", "office", FinanceCategoryType.EXPENSE),
    ("Travel", "travel", FinanceCategoryType.EXPENSE),
    ("Entertainment", "entertainment", FinanceCategoryType.EXPENSE),
    ("Health", "health", FinanceCategoryType.EXPENSE),
    ("Family", "family", FinanceCategoryType.EXPENSE),
    ("Other", "other", FinanceCategoryType.EXPENSE),
    ("Salary", "salary", FinanceCategoryType.INCOME),
    ("Business Income", "business-income", FinanceCategoryType.INCOME),
    ("Transfer", "transfer", FinanceCategoryType.INCOME),
    ("Refund", "refund", FinanceCategoryType.INCOME),
    ("Other Income", "other-income", FinanceCategoryType.INCOME),
)

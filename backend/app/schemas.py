from datetime import date, datetime
from pydantic import BaseModel
from typing import Optional

from app.models.account import AccountType
from app.models.transaction import TransactionCategory, TransactionType
from app.models.income import IncomeFrequency
from app.models.debt import PayoffStrategy


# ── Account ──
class AccountCreate(BaseModel):
    name: str
    account_type: AccountType
    institution: str = ""
    balance: float = 0
    interest_rate: float = 0
    credit_limit: Optional[float] = None
    minimum_payment: float = 0
    due_day: int = 1


class AccountOut(AccountCreate):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Transaction ──
class TransactionCreate(BaseModel):
    account_id: int
    date: date
    amount: float
    transaction_type: TransactionType
    category: TransactionCategory = TransactionCategory.OTHER
    description: str = ""
    merchant: str = ""
    notes: str = ""
    is_recurring: bool = False
    is_essential: bool = False


class TransactionOut(TransactionCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Debt ──
class DebtCreate(BaseModel):
    account_id: Optional[int] = None
    name: str
    current_balance: float
    interest_rate: float
    minimum_payment: float
    credit_limit: Optional[float] = None
    due_day: int = 1


class DebtOut(DebtCreate):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PayoffRequest(BaseModel):
    strategy: PayoffStrategy = PayoffStrategy.AVALANCHE
    extra_monthly_payment: float = 0


class PayoffStep(BaseModel):
    month: int
    debt_name: str
    payment: float
    remaining_balance: float
    interest_charged: float


class PayoffResult(BaseModel):
    strategy: PayoffStrategy
    total_months: int
    total_interest_paid: float
    total_paid: float
    monthly_plan: list[PayoffStep]
    payoff_order: list[str]


# ── Budget ──
class BudgetCreate(BaseModel):
    category: TransactionCategory
    monthly_limit: float
    alert_threshold: float = 0.80


class BudgetOut(BudgetCreate):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


# ── Income ──
class IncomeCreate(BaseModel):
    source: str
    amount: float
    frequency: IncomeFrequency
    next_pay_date: Optional[date] = None


class IncomeOut(IncomeCreate):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Dashboard ──
class DashboardSummary(BaseModel):
    total_income_monthly: float
    total_expenses_monthly: float
    net_monthly: float
    total_debt: float
    total_minimum_payments: float
    debt_to_income_ratio: float
    expenses_by_category: dict[str, float]
    essential_vs_discretionary: dict[str, float]
    top_cuts: list[dict]


# ── NLP Transaction Entry ──
class NLPTransactionInput(BaseModel):
    text: str
    account_id: int


class NLPParseResult(BaseModel):
    parsed: dict
    confidence: str  # "high", "medium", "low"
    needs_review: bool


# ── Forecasting ──
class ForecastRequest(BaseModel):
    months_ahead: int = 6
    categories: list[str] = []  # empty = all categories


class CategoryForecast(BaseModel):
    category: str
    months: list[str]
    predicted: list[float]
    lower_bound: list[float]
    upper_bound: list[float]
    trend: str
    pct_change: float


class DebtFreeProjection(BaseModel):
    current_months: int
    current_interest: float
    optimistic_months: int
    optimistic_interest: float
    forecasted_months: int
    forecasted_interest: float


class ForecastResponse(BaseModel):
    category_forecasts: list[CategoryForecast]
    debt_free_projection: DebtFreeProjection
    overall_expense_trend: str
    alert_categories: list[dict]  # categories trending up > 25%


# ── Subscriptions ──
class SubscriptionOut(BaseModel):
    merchant: str
    category: str
    avg_amount: float
    frequency_days: int
    occurrence_count: int
    last_charged: date
    total_spent: float
    waste_score: int
    suggestion: str
    action: str = ""  # cancel, downgrade, negotiate, keep
    cancel_difficulty: str = ""  # easy, medium, hard
    cancel_method: str = ""  # how to cancel
    annual_cost: float = 0
    alternatives: str = ""  # free/cheaper alternatives


# ── Health Score ──
class HealthScoreResponse(BaseModel):
    overall_score: int
    grade: str
    components: dict[str, dict]
    tips: list[str]
    trend: str


# ── Coaching ──
class CoachingNudge(BaseModel):
    message: str
    generated_at: datetime


# ── Scenarios ──
class ScenarioRequest(BaseModel):
    extra_amounts: list[float] = [0, 50, 100, 200, 300, 500]
    windfall: float = 0
    windfall_target: str = "highest_interest"


class ScenarioOut(BaseModel):
    name: str
    strategy: str
    extra_monthly: float
    total_months: int
    total_interest: float
    total_paid: float
    months_saved_vs_minimum: int
    interest_saved_vs_minimum: float


# ── Feedback ──
class FeedbackCreate(BaseModel):
    entity_type: str  # "categorization", "forecast", "waste_score", "nudge"
    entity_id: Optional[int] = None
    original_value: str = ""
    corrected_value: str = ""
    is_positive: bool
    comment: str = ""


class FeedbackOut(FeedbackCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AccuracyMetrics(BaseModel):
    metrics: dict[str, dict]

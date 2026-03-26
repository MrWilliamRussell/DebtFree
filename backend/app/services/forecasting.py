"""Time-series forecasting for spending prediction and debt timeline.

Uses Amazon Chronos for probabilistic forecasting of monthly spending patterns.
Falls back to simple exponential smoothing if Chronos unavailable.
"""

import numpy as np
from dataclasses import dataclass

try:
    import torch
    from chronos import ChronosPipeline
    CHRONOS_AVAILABLE = True
except ImportError:
    CHRONOS_AVAILABLE = False


@dataclass
class ForecastResult:
    months_ahead: list[str]  # ["2026-04", "2026-05", ...]
    predicted_values: list[float]
    lower_bound: list[float]  # 20th percentile
    upper_bound: list[float]  # 80th percentile
    trend: str  # "rising", "falling", "stable"
    pct_change: float  # predicted % change over forecast horizon


_pipeline = None


def _get_chronos_pipeline():
    global _pipeline
    if _pipeline is None and CHRONOS_AVAILABLE:
        _pipeline = ChronosPipeline.from_pretrained(
            "amazon/chronos-t5-small",
            device_map="auto",
            torch_dtype=torch.float32,
        )
    return _pipeline


def forecast_category_spending(
    monthly_values: list[float],
    months_ahead: int = 6,
    month_labels: list[str] | None = None,
) -> ForecastResult:
    """Forecast future spending for a category given historical monthly totals.

    Args:
        monthly_values: List of monthly spending totals (at least 3 months).
        months_ahead: Number of months to forecast.
        month_labels: Optional labels for the forecast months.
    """
    if len(monthly_values) < 3:
        # Not enough data, return flat projection
        avg = np.mean(monthly_values) if monthly_values else 0
        labels = month_labels or [f"M+{i+1}" for i in range(months_ahead)]
        return ForecastResult(
            months_ahead=labels[:months_ahead],
            predicted_values=[round(avg, 2)] * months_ahead,
            lower_bound=[round(avg * 0.8, 2)] * months_ahead,
            upper_bound=[round(avg * 1.2, 2)] * months_ahead,
            trend="stable",
            pct_change=0.0,
        )

    labels = month_labels or [f"M+{i+1}" for i in range(months_ahead)]

    pipeline = _get_chronos_pipeline()
    if pipeline is not None:
        return _forecast_chronos(pipeline, monthly_values, months_ahead, labels)
    else:
        return _forecast_ema(monthly_values, months_ahead, labels)


def _forecast_chronos(pipeline, values: list[float], horizon: int, labels: list[str]) -> ForecastResult:
    """Use Chronos for probabilistic forecasting."""
    context = torch.tensor([values], dtype=torch.float32)
    forecast = pipeline.predict(context, horizon)  # shape: (1, num_samples, horizon)

    # Extract quantiles
    median = np.median(forecast[0].numpy(), axis=0)
    low = np.percentile(forecast[0].numpy(), 20, axis=0)
    high = np.percentile(forecast[0].numpy(), 80, axis=0)

    predicted = [round(float(v), 2) for v in median]
    lower = [round(float(v), 2) for v in low]
    upper = [round(float(v), 2) for v in high]

    trend = _detect_trend(values, predicted)
    pct = _pct_change(values[-1], predicted[-1]) if values else 0.0

    return ForecastResult(
        months_ahead=labels[:horizon],
        predicted_values=predicted,
        lower_bound=lower,
        upper_bound=upper,
        trend=trend,
        pct_change=round(pct, 1),
    )


def _forecast_ema(values: list[float], horizon: int, labels: list[str]) -> ForecastResult:
    """Exponential moving average fallback when Chronos is unavailable."""
    alpha = 0.3
    ema = values[0]
    for v in values[1:]:
        ema = alpha * v + (1 - alpha) * ema

    # Simple trend continuation
    if len(values) >= 2:
        recent_trend = (values[-1] - values[-3]) / max(abs(values[-3]), 1) if len(values) >= 3 else 0
        monthly_drift = ema * (recent_trend / 3)
    else:
        monthly_drift = 0

    predicted = []
    lower = []
    upper = []
    current = ema
    std = float(np.std(values)) if len(values) > 1 else ema * 0.1

    for i in range(horizon):
        current += monthly_drift
        current = max(current, 0)
        predicted.append(round(current, 2))
        lower.append(round(max(current - std * (1 + 0.1 * i), 0), 2))
        upper.append(round(current + std * (1 + 0.1 * i), 2))

    trend = _detect_trend(values, predicted)
    pct = _pct_change(values[-1], predicted[-1]) if values else 0.0

    return ForecastResult(
        months_ahead=labels[:horizon],
        predicted_values=predicted,
        lower_bound=lower,
        upper_bound=upper,
        trend=trend,
        pct_change=round(pct, 1),
    )


def _detect_trend(historical: list[float], forecast: list[float]) -> str:
    if not forecast or not historical:
        return "stable"
    avg_hist = np.mean(historical[-3:])
    avg_fore = np.mean(forecast)
    pct = (avg_fore - avg_hist) / max(abs(avg_hist), 1) * 100
    if pct > 10:
        return "rising"
    elif pct < -10:
        return "falling"
    return "stable"


def _pct_change(old: float, new: float) -> float:
    if abs(old) < 0.01:
        return 0.0
    return (new - old) / abs(old) * 100


def forecast_debt_free_date(
    total_debt: float,
    monthly_payment: float,
    avg_interest_rate: float,
    monthly_income: float,
    monthly_expenses: float,
    forecast_expense_change_pct: float = 0.0,
) -> dict:
    """Predict when you'll be debt-free given current trajectory and forecasted changes.

    Returns scenarios: current path, optimistic (cut 15%), and with forecasted expense changes.
    """
    scenarios = {}

    for name, expense_mult in [
        ("current", 1.0),
        ("optimistic_15pct_cut", 0.85),
        ("forecasted", 1.0 + forecast_expense_change_pct / 100),
    ]:
        adjusted_expenses = monthly_expenses * expense_mult
        available_for_debt = max(monthly_income - adjusted_expenses, monthly_payment)
        months = _simulate_payoff(total_debt, available_for_debt, avg_interest_rate)
        scenarios[name] = {
            "months_to_payoff": months,
            "monthly_available": round(available_for_debt, 2),
            "total_interest": round(_total_interest(total_debt, available_for_debt, avg_interest_rate, months), 2),
        }

    return scenarios


def _simulate_payoff(balance: float, monthly_payment: float, annual_rate: float) -> int:
    monthly_rate = annual_rate / 100 / 12
    months = 0
    remaining = balance
    while remaining > 0.01 and months < 600:
        interest = remaining * monthly_rate
        remaining = remaining + interest - monthly_payment
        months += 1
        if monthly_payment <= interest:
            return 999  # Will never pay off at this rate
    return months


def _total_interest(balance: float, monthly_payment: float, annual_rate: float, months: int) -> float:
    monthly_rate = annual_rate / 100 / 12
    total_interest = 0.0
    remaining = balance
    for _ in range(min(months, 600)):
        interest = remaining * monthly_rate
        total_interest += interest
        remaining = remaining + interest - monthly_payment
        if remaining <= 0:
            break
    return total_interest

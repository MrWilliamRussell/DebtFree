"""Multi-scenario debt optimization engine.

Runs dozens of payoff strategy variations automatically and finds the optimal path
considering interest rate changes, windfalls, and spending cuts.
"""

from dataclasses import dataclass
from itertools import product


@dataclass
class ScenarioResult:
    name: str
    strategy: str
    extra_monthly: float
    total_months: int
    total_interest: float
    total_paid: float
    months_saved_vs_minimum: int
    interest_saved_vs_minimum: float


@dataclass
class DebtInput:
    name: str
    balance: float
    interest_rate: float
    minimum_payment: float


def run_scenario_matrix(
    debts: list[DebtInput],
    extra_amounts: list[float] = None,
    windfall: float = 0,
    apply_windfall_to: str = "highest_interest",
) -> list[ScenarioResult]:
    """Run multiple debt payoff scenarios and rank them.

    Args:
        debts: List of active debts.
        extra_amounts: List of extra monthly payments to simulate (e.g., [0, 50, 100, 200, 500]).
        windfall: One-time extra payment to apply.
        apply_windfall_to: "highest_interest", "smallest_balance", or a specific debt name.
    """
    if not debts:
        return []

    if extra_amounts is None:
        extra_amounts = [0, 50, 100, 200, 300, 500]

    strategies = ["avalanche", "snowball"]
    results = []

    # Calculate baseline (minimum payments only)
    baseline = _simulate(debts, "avalanche", 0, 0, "")
    baseline_months = baseline[0]
    baseline_interest = baseline[1]

    for strategy, extra in product(strategies, extra_amounts):
        months, interest, total = _simulate(debts, strategy, extra, windfall, apply_windfall_to)

        name_parts = [strategy.title()]
        if extra > 0:
            name_parts.append(f"+${extra}/mo")
        if windfall > 0:
            name_parts.append(f"+${windfall:.0f} windfall")

        results.append(ScenarioResult(
            name=" | ".join(name_parts),
            strategy=strategy,
            extra_monthly=extra,
            total_months=months,
            total_interest=round(interest, 2),
            total_paid=round(total, 2),
            months_saved_vs_minimum=baseline_months - months,
            interest_saved_vs_minimum=round(baseline_interest - interest, 2),
        ))

    # Sort by total interest paid (ascending = best first)
    results.sort(key=lambda r: r.total_interest)
    return results


def _simulate(
    debts: list[DebtInput],
    strategy: str,
    extra_monthly: float,
    windfall: float,
    windfall_target: str,
) -> tuple[int, float, float]:
    """Simulate a payoff scenario. Returns (months, total_interest, total_paid)."""
    balances = {d.name: d.balance for d in debts}
    rates = {d.name: d.interest_rate for d in debts}
    mins = {d.name: d.minimum_payment for d in debts}

    # Apply windfall
    if windfall > 0:
        target = _pick_target(debts, windfall_target, balances)
        if target:
            balances[target] = max(balances[target] - windfall, 0)

    total_interest = 0.0
    total_paid = 0.0
    month = 0
    freed_extra = 0.0

    while any(b > 0.01 for b in balances.values()) and month < 600:
        month += 1
        active = {k: v for k, v in balances.items() if v > 0.01}
        if not active:
            break

        # Pick target for extra payment
        if strategy == "avalanche":
            target = max(active, key=lambda k: rates[k])
        else:
            target = min(active, key=lambda k: balances[k])

        available_extra = extra_monthly + freed_extra

        for name in list(balances.keys()):
            if balances[name] <= 0.01:
                continue

            # Interest
            interest = balances[name] * rates[name] / 100 / 12
            total_interest += interest
            balances[name] += interest

            # Payment
            payment = min(mins[name], balances[name])
            if name == target:
                payment += available_extra
                available_extra = 0

            payment = min(payment, balances[name])
            balances[name] -= payment
            total_paid += payment

            if balances[name] <= 0.01:
                balances[name] = 0
                freed_extra += mins[name]

    return month, total_interest, total_paid


def _pick_target(debts: list[DebtInput], strategy: str, balances: dict[str, float]) -> str | None:
    active = [d for d in debts if balances.get(d.name, 0) > 0]
    if not active:
        return None

    if strategy == "highest_interest":
        return max(active, key=lambda d: d.interest_rate).name
    elif strategy == "smallest_balance":
        return min(active, key=lambda d: balances[d.name]).name
    else:
        # Specific debt name
        matches = [d for d in active if d.name == strategy]
        return matches[0].name if matches else active[0].name

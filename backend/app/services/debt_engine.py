"""Debt payoff calculator supporting Avalanche and Snowball strategies."""

from dataclasses import dataclass
from app.models.debt import Debt, PayoffStrategy
from app.schemas import PayoffResult, PayoffStep


@dataclass
class DebtState:
    name: str
    balance: float
    interest_rate: float
    minimum_payment: float


def calculate_payoff_plan(
    debts: list[Debt],
    strategy: PayoffStrategy,
    extra_monthly: float = 0,
) -> PayoffResult:
    """Calculate a complete debt payoff plan.

    Avalanche: pay minimums on all, throw extra at highest interest rate.
    Snowball: pay minimums on all, throw extra at smallest balance.
    """
    states = [
        DebtState(
            name=d.name,
            balance=float(d.current_balance),
            interest_rate=float(d.interest_rate),
            minimum_payment=float(d.minimum_payment),
        )
        for d in debts
        if float(d.current_balance) > 0
    ]

    monthly_plan: list[PayoffStep] = []
    payoff_order: list[str] = []
    total_interest = 0.0
    total_paid = 0.0
    month = 0
    max_months = 360  # 30-year safety cap

    while any(s.balance > 0 for s in states) and month < max_months:
        month += 1

        # Determine which debt gets the extra payment
        active = [s for s in states if s.balance > 0]
        if not active:
            break

        if strategy == PayoffStrategy.AVALANCHE:
            target = max(active, key=lambda s: s.interest_rate)
        else:  # SNOWBALL
            target = min(active, key=lambda s: s.balance)

        extra_remaining = extra_monthly

        for state in states:
            if state.balance <= 0:
                continue

            # Monthly interest
            monthly_rate = state.interest_rate / 100 / 12
            interest = state.balance * monthly_rate
            total_interest += interest
            state.balance += interest

            # Payment
            payment = min(state.minimum_payment, state.balance)
            if state is target:
                payment += extra_remaining

            payment = min(payment, state.balance)
            state.balance -= payment
            total_paid += payment

            monthly_plan.append(PayoffStep(
                month=month,
                debt_name=state.name,
                payment=round(payment, 2),
                remaining_balance=round(max(state.balance, 0), 2),
                interest_charged=round(interest, 2),
            ))

            # Check if just paid off
            if state.balance <= 0.01:
                state.balance = 0
                if state.name not in payoff_order:
                    payoff_order.append(state.name)
                # Freed-up minimum goes to extra pool next month
                extra_monthly += state.minimum_payment

    return PayoffResult(
        strategy=strategy,
        total_months=month,
        total_interest_paid=round(total_interest, 2),
        total_paid=round(total_paid, 2),
        monthly_plan=monthly_plan,
        payoff_order=payoff_order,
    )

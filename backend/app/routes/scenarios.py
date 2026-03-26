"""Multi-scenario debt optimization routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.debt import Debt
from app.schemas import ScenarioRequest, ScenarioOut
from app.services.scenario_optimizer import run_scenario_matrix, DebtInput

router = APIRouter()


@router.post("/optimize", response_model=list[ScenarioOut])
async def optimize_payoff(req: ScenarioRequest, db: AsyncSession = Depends(get_db)):
    """Run dozens of payoff scenarios and rank by total interest saved."""
    result = await db.execute(select(Debt).where(Debt.is_active == True))
    debts = result.scalars().all()

    if not debts:
        raise HTTPException(status_code=400, detail="No active debts")

    inputs = [
        DebtInput(
            name=d.name,
            balance=float(d.current_balance),
            interest_rate=float(d.interest_rate),
            minimum_payment=float(d.minimum_payment),
        )
        for d in debts
    ]

    results = run_scenario_matrix(
        debts=inputs,
        extra_amounts=req.extra_amounts,
        windfall=req.windfall,
        apply_windfall_to=req.windfall_target,
    )

    return [
        ScenarioOut(
            name=r.name,
            strategy=r.strategy,
            extra_monthly=r.extra_monthly,
            total_months=r.total_months,
            total_interest=r.total_interest,
            total_paid=r.total_paid,
            months_saved_vs_minimum=r.months_saved_vs_minimum,
            interest_saved_vs_minimum=r.interest_saved_vs_minimum,
        )
        for r in results
    ]

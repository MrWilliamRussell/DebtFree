from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import (
    accounts, transactions, debts, budgets, dashboard, imports,
    nlp, forecast, subscriptions, health, scenarios, feedback, reports,
)
from app.routes import automation, overview
from app.database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from app.models import Account, Transaction, Debt, Budget, Income  # noqa: F401
    from app.models.connected_account import ConnectedAccount  # noqa: F401
    from app.services.feedback_loop import UserFeedback  # noqa: F401
    from app.services.credential_vault import StoredCredential  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Start background scheduler
    from app.services.scheduler import setup_scheduler
    setup_scheduler()

    yield

    # Shutdown
    from app.services.scheduler import scheduler
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="DebtFree - AI-Powered Debt Elimination Dashboard",
    description="Self-hosted personal finance with automated bank sync, AI categorization, and debt payoff optimization",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3088", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core routes
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(accounts.router, prefix="/api/accounts", tags=["Accounts"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(debts.router, prefix="/api/debts", tags=["Debts"])
app.include_router(budgets.router, prefix="/api/budgets", tags=["Budgets"])
app.include_router(imports.router, prefix="/api/imports", tags=["Imports"])

# AI-powered routes
app.include_router(nlp.router, prefix="/api/nlp", tags=["NLP Entry"])
app.include_router(forecast.router, prefix="/api/forecast", tags=["Forecasting"])
app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["Subscriptions"])
app.include_router(health.router, prefix="/api/health", tags=["Health Score"])
app.include_router(scenarios.router, prefix="/api/scenarios", tags=["Scenarios"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])

# System overview
app.include_router(overview.router, prefix="/api/overview", tags=["Overview"])

# Automation routes
app.include_router(automation.router, prefix="/api/automation", tags=["Automation"])


@app.get("/api/ping")
async def ping():
    return {"status": "ok", "version": "0.3.0"}

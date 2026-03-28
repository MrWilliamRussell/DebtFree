from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.limiters import Limiter

limiter = Limiter(key_func=get_remote_address)

# Define rate limits
normal_rate_limit = limiter.limit("100 per minute")
expensive_rate_limit = limiter.limit("10 per minute")

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

# Add rate limiting middleware
@app.middleware("http")
async def add_rate_limiting(request: Request, call_next):
    try:
        response = await limiter(request, call_next)
    except RateLimitExceeded as e:
        headers = {"Retry-After": str(e.retry_after)}
        raise HTTPException(status_code=429, detail="Too Many Requests", headers=headers)
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3088", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core routes
@app.get("/api/ping")
@normal_rate_limit
async def ping():
    return {"status": "ok", "version": "0.3.0"}

app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(accounts.router, prefix="/api/accounts", tags=["Accounts"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(debts.router, prefix="/api/debts", tags=["Debts"])
app.include_router(budgets.router, prefix="/api/budgets", tags=["Budgets"])
app.include_router(imports.router, prefix="/api/imports", tags=["Imports"])

# AI-powered routes
app.include_router(nlp.router, prefix="/api/nlp", tags=["NLP Entry"], dependencies=[expensive_rate_limit])
app.include_router(forecast.router, prefix="/api/forecast", tags=["Forecasting"], dependencies=[expensive_rate_limit])
app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["Subscriptions"])
app.include_router(health.router, prefix="/api/health", tags=["Health Score"])
app.include_router(scenarios.router, prefix="/api/scenarios", tags=["Scenarios"], dependencies=[expensive_rate_limit])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])

# System overview
app.include_router(overview.router, prefix="/api/overview", tags=["Overview"])

# Automation routes
app.include_router(automation.router, prefix="/api/automation", tags=["Automation"])
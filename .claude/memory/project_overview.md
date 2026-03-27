---
name: Project Overview
description: Dockerized personal finance debt-elimination dashboard with Python/FastAPI backend, React frontend, Qdrant vector search, PostgreSQL, and Discord alerting
type: project
---

Full-stack self-hosted personal finance and debt payoff platform.

**Stack:** Docker Compose with FastAPI (Python), React (Vite + Recharts), PostgreSQL, Qdrant, Discord webhooks/bot.

**Core Features:**
- Bank/credit card/Amazon transaction scanning (CSV/OFX import, optional Plaid API)
- Income vs expense tracking with categorization (gas, rent, food, etc.)
- Credit card interest rate tracking
- Debt payoff engine (avalanche/snowball methods)
- Dashboard with charts and "what to cut" suggestions
- Qdrant for fast semantic indexing of transactions
- PostgreSQL for SQL backups
- Discord alerts for budget thresholds and milestones

**Why:** User wants to actively manage finances, visualize spending, and create a concrete plan to get out of debt.

**How to apply:** All features should prioritize practical debt reduction. Keep the UI actionable — not just pretty charts but clear recommendations.

**Key reference repos:** Firefly III (importers), FinanceTracker (Python+React pattern), expense-tracking-discord-bot (Discord alerts), Undebt.it/calculator.net (payoff algorithms).

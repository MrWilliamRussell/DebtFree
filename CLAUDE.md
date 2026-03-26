# DebtFree - AI-Powered Debt Elimination Dashboard

## Project Overview
Self-hosted, privacy-first personal finance dashboard with AI-powered forecasting, coaching, and debt payoff optimization. Tracks income, expenses, bank accounts, credit cards, and provides intelligent insights via local LLM (Ollama) and time-series forecasting (Chronos).

## Tech Stack
- **Backend**: Python 3.12 / FastAPI / SQLAlchemy (async) / PostgreSQL
- **Frontend**: React 18 / Vite / Tailwind CSS / Recharts / Lucide icons
- **AI/ML**: Ollama (local LLM - Mistral), Chronos (time-series forecasting), sentence-transformers
- **Vector Search**: Qdrant (semantic transaction indexing + RAG)
- **Bank Sync**: Plaid API (secure token-based OAuth — never stores bank passwords)
- **Alerts & Coaching**: Discord webhooks (budget alerts, coaching nudges, anomaly warnings)
- **Caching**: Redis
- **Infrastructure**: Docker Compose (7 services)

## Quick Start
```bash
cp .env.example .env   # Edit with your secrets & ports
docker compose up --build
# Pull the LLM model on first run:
docker exec finance_ollama ollama pull mistral
```

## Ports (configurable in .env)
| Service    | Port  |
|------------|-------|
| Frontend   | 3088  |
| Backend    | 8088  |
| PostgreSQL | 5433  |
| Qdrant HTTP| 6340  |
| Qdrant gRPC| 6341  |
| Ollama     | 11434 |
| Redis      | 6380  |

## URLs
- Frontend: http://localhost:3088
- Backend Swagger: http://localhost:8088/docs
- Qdrant Dashboard: http://localhost:6340/dashboard

## Project Structure
```
backend/
  app/
    main.py              # FastAPI entry, router registration
    config.py            # Pydantic settings from env
    database.py          # Async SQLAlchemy + PostgreSQL
    schemas.py           # All Pydantic request/response models
    models/              # ORM: Account, Transaction, Debt, Budget, Income
      connected_account.py  # Plaid-linked bank accounts (stores tokens, NOT passwords)
    routes/
      accounts.py        # Account CRUD + Plaid bank connection endpoints
      transactions.py    # Transaction CRUD with filter/sort
      debts.py           # Debt CRUD + payoff calculator
      budgets.py         # Budget CRUD
      dashboard.py       # Summary + income endpoints
      imports.py         # CSV/Amazon import with hybrid AI categorization
      nlp.py             # Natural language transaction entry
      forecast.py        # Time-series spending predictions
      subscriptions.py   # Recurring charge detection + waste scoring
      health.py          # Financial health score + AI coach
      scenarios.py       # Multi-scenario debt optimization
      feedback.py        # User feedback loop for LLM improvement
      reports.py         # PDF report generation
    services/
      plaid_service.py       # Secure bank sync (Plaid Link + transaction pull)
      amazon_importer.py     # Amazon order history CSV parser
      debt_engine.py         # Avalanche & Snowball payoff calculator
      discord_alerts.py      # Budget threshold → Discord webhook
      qdrant_service.py      # Semantic transaction search
      nlp_parser.py          # Ollama-based NLP parser + waste scorer + categorizer
      forecasting.py         # Chronos time-series + EMA fallback
      subscription_detector.py  # Recurring charge detection + cancel/keep/negotiate
      health_score.py        # 0-100 composite financial health score
      coaching.py            # Behavioral nudges + milestone alerts
      scenario_optimizer.py  # Multi-scenario matrix optimizer
      report_generator.py    # PDF with ReportLab + matplotlib charts
      feedback_loop.py       # UserFeedback model + accuracy metrics

frontend/
  src/
    App.jsx              # Sidebar nav (Core + AI Tools sections) + routing
    api.js               # Axios client for all 30+ endpoints
    pages/
      Dashboard.jsx      # Summary cards, pie/bar charts, cut suggestions
      Accounts.jsx       # Bank/CC account management cards
      Transactions.jsx   # Transaction list + add form
      Debts.jsx          # Debt table + payoff planner with line chart
      Budgets.jsx        # Budget limits + Discord alert config
      Import.jsx         # CSV/Amazon upload + Plaid live sync tab
      NLPEntry.jsx       # Natural language "quick entry" with preview
      Forecast.jsx       # Spending predictions + debt-free timeline
      Subscriptions.jsx  # Auto-detected subs + cancel methods + AI analysis
      HealthScore.jsx    # Ring chart score + component breakdown + AI coach
      Scenarios.jsx      # Multi-scenario comparison table + bar chart
      Reports.jsx        # PDF download page
```

## Data Ingestion Methods
1. **CSV Import** — Bank/credit card statement exports (auto-categorized)
2. **Amazon Import** — Amazon order history CSV with product-level categorization
3. **Plaid Live Sync** — Secure bank connection via OAuth (token-based, never stores passwords)
4. **Natural Language** — Type "Spent $45 on gas at Shell" → AI parses and saves
5. **Manual Entry** — Traditional form-based transaction entry

## Transaction Categorization Pipeline
1. **Rule-based** (instant) — 60+ merchant keyword rules
2. **Plaid categories** — When synced via Plaid, their ML categories are mapped
3. **LLM fallback** — Ollama/Mistral categorizes anything rules miss
4. **User feedback** — Corrections stored for future LoRA fine-tuning

## Key Conventions
- All monetary amounts: Numeric(12,2) in PostgreSQL
- Bank credentials NEVER stored — Plaid uses secure token-based OAuth
- Debt payoff supports Avalanche (highest interest) and Snowball (smallest balance)
- Time-series forecasting uses Chronos with EMA fallback
- NLP parsing uses Ollama local LLM (Mistral by default)
- Discord alerts fire on budget thresholds, anomalies, and milestones
- User feedback stored for periodic LoRA fine-tuning
- Backend is fully async (asyncpg + async SQLAlchemy)
- Frontend uses Tailwind dark theme throughout

## Environment Variables
See `.env.example` for all configuration. Key ones:
- Port overrides: `FRONTEND_PORT`, `BACKEND_PORT`, `POSTGRES_PORT`, etc.
- `DISCORD_WEBHOOK_URL` - for budget alerts and coaching
- `OLLAMA_MODEL` - which LLM to use (default: mistral)
- `PLAID_CLIENT_ID` / `PLAID_SECRET` - optional live bank sync

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current Branch

**`feature/ia-demo`** — extends `main` with card management (HU-015/016), admin authentication, a chatbot feature, and a Streamlit demo dependency group.

## Project Overview

Fraud Detection Engine — a microservices-based fintech system with event-driven processing. Implements Clean Architecture (Hexagonal) with Strategy Pattern for pluggable fraud detection rules and TDD/BDD methodology.

## Commands

### Backend (Python/Poetry)

```bash
# Install dependencies (includes demo group with Streamlit)
poetry install

# Run unit tests
pytest tests/unit/ -v

# Run with coverage (minimum 70% enforced)
pytest tests/unit/ --cov=services --cov-report=html --cov-fail-under=70

# Run a single test file
pytest tests/unit/test_fraud_strategies.py -v

# Run a single test by name
pytest tests/unit/test_fraud_strategies.py::TestAmountThreshold::test_high_amount -v

# Code quality
poetry run black services/       # Format
poetry run pylint services/      # Lint
poetry run mypy services/        # Type check

# Validate Clean Architecture (no domain→infrastructure imports)
python scripts/validate_architecture.py
```

### Frontend

```bash
# User app (port 5173 dev / 3000 Docker)
cd frontend/user-app && npm install && npm run dev
npm test              # Vitest
npm run test:coverage
npm run build

# Admin dashboard (port 3001 dev and Docker)
cd frontend/admin-dashboard && npm install && npm run dev
npm test
npm run build
```

### Infrastructure

```bash
# Start all services (MongoDB, Redis, RabbitMQ, API, Worker, Frontends)
docker-compose up -d

# Start infrastructure only
docker-compose up mongodb redis rabbitmq -d

# E2E tests
cd tests-e2e && npm install && npx playwright test
npx playwright test --ui
npx playwright test --headed
npx playwright test --debug
npx playwright test tests/admin-dashboard.spec.ts   # single spec
npx playwright test --project=chromium              # specific browser
```

## Architecture

### Service Layout

```
services/
  api-gateway/               # FastAPI REST API (port 8000)
  fraud-evaluation-service/  # Core domain logic
  worker-service/            # RabbitMQ consumer
frontend/
  user-app/                  # User transaction dashboard (React/Vite/TS, port 5173/3000)
  admin-dashboard/           # Admin metrics dashboard (React/Vite/TS, port 3001)
tests/
  unit/                      # 36 test files
  integration/               # 6 test files (card repo, card API, auth, RabbitMQ)
  fixtures/                  # Shared JSON test data
tests-e2e/
  tests/                     # 13 Playwright specs (HU-001 through HU-016 + chatbot)
  pages/                     # Page Object Model (BasePage, CardPage, RulesPage, etc.)
docs/
  user-stories/              # 16 HU markdown files
  ARCHITECTURE.md, CARDS-API.md, CONTEXT.md, DEPLOYMENT-CARDS.md
```

### Request Flow

1. Client → POST `/transaction` → **API Gateway** (FastAPI)
2. API Gateway publishes to **RabbitMQ** queue
3. **Worker Service** consumes messages asynchronously
4. **Fraud Strategies** evaluate transaction (Strategy Pattern)
5. Results stored in **MongoDB**, cached in **Redis**
6. Frontends query results via API

### Clean Architecture Layers (fraud-evaluation-service)

- **Domain** (`src/domain/`): `Transaction`, `Card`, `FraudEvaluation`, `Location` models; `FraudStrategy` ABC; 5 concrete strategies; `card_validators.py`. No external dependencies.
- **Application** (`src/application/`): Main use cases (`EvaluateTransactionUseCase`, `ReviewTransactionUseCase`); auth use cases (`RegisterUser`, `LoginUser`, `VerifyEmail`); admin auth use cases; card use cases (`AddCard`, `GetCardDetails`, `ListUserCards`, `RemoveCard`) under `src/application/use_cases/`; ports (`card_repository.py`, `audit_publisher.py`).
- **Infrastructure** (`src/infrastructure/`): `user_repository.py`, `admin_repository.py`, `auth_service.py`; adapters under `adapters/mongodb/` (card repository) and `adapters/rabbitmq/` (audit event publisher).
- **Interface** (`src/routes.py`, `src/auth_routes.py`): FastAPI routes with Dependency Injection.
- **Factory** (`src/adapters.py`): Wires ports to concrete implementations.

### Fraud Detection Strategies

Five pluggable strategies (all extend `FraudStrategy` ABC in `src/domain/strategies/base.py`):
- `AmountThresholdStrategy` — flags transactions > $1,500 (configurable via `AMOUNT_THRESHOLD`)
- `LocationStrategy` — flags > 100 km from usual location (configurable via `LOCATION_RADIUS_KM`)
- `RapidTransactionStrategy` — detects rapid sequential transactions
- `UnusualTimeStrategy` — flags transactions at unusual hours
- `DeviceValidationStrategy` — validates device consistency

### Infrastructure Services

- **MongoDB 7.0** (27017): Persistent storage for transactions, evaluations, users, admins, cards
- **Redis 7.2** (6379): Caching and session management
- **RabbitMQ 3.12** (5672): Async message queue; management UI at port 15672

## Testing

Tests under `tests/` with fixtures in `tests/fixtures/` and shared setup in `conftest.py`. Test markers: `unit`, `integration`, `slow`, `asyncio`.

E2E specs map to user stories: `hu-001` through `hu-016` plus `chatbot.spec.ts` and `admin-dashboard.spec.ts`. Page Objects are in `tests-e2e/pages/`. Playwright runs Chromium with 120s timeout, 3 parallel workers, 2 retries in CI.

CI (`github/workflows/ci.yml`) runs three jobs: **build** → **test-backend** (against live MongoDB/Redis/RabbitMQ) → **sonarqube**. Coverage XML is uploaded as an artifact and consumed by SonarQube.

## Configuration

Copy `.env.example` → `.env` (or `.env.local.example` for Docker-internal hostnames). Key env vars:
- `AMOUNT_THRESHOLD` (default: 1500.0) — fraud amount threshold
- `LOCATION_RADIUS_KM` (default: 100.0) — unusual location radius
- `MONGODB_URL`, `REDIS_URL`, `RABBITMQ_URL` — connection strings
- `MONGODB_DATABASE` (default: fraud_detection)

Dynamic fraud rule thresholds can be modified at runtime via `/config/*` endpoints without redeployment.

## Key Patterns

- **Strategy Pattern**: Add new fraud rules by extending `FraudStrategy` ABC — no existing code changes required.
- **Dependency Injection**: FastAPI dependencies inject adapters into use cases, keeping all application logic testable with mocks.
- **Value Objects**: `Location` is an immutable dataclass with built-in validation; `RiskLevel` is a typed Enum (LOW=1, MEDIUM=2, HIGH=3).
- **Architecture validation**: `scripts/validate_architecture.py` checks that Domain never imports from Infrastructure (enforces Clean Architecture at dev time).
- **"HUMAN REVIEW" comments**: Inline decision notes by María Gutiérrez explain non-obvious design choices throughout the codebase.

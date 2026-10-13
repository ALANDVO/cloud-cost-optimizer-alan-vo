# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

frontend-core

## Roadmap

### backend-core — FastAPI Backend Core with Domain Logic

Status: done

Acceptance:
- FastAPI app exports create_app factory
- Domain services for AWS/GCP/Azure cost analysis
- REST API endpoints for analyze, waste, rightsize, ask, plan
- SQLite persistence for analyses and recommendations
- Authentication with OIDC/Keycloak (demo mode for localhost)

Implementation: `backend/app/main.py`, `backend/app/api/routes/health.py`, `backend/app/api/routes/auth.py`, `backend/app/api/routes/analysis.py`, `backend/app/services/aws.py`, `backend/app/services/gcp.py`, `backend/app/services/azure.py`, `backend/app/services/llm.py`, `backend/app/services/analysis.py`, `backend/app/models/analysis.py`, `backend/app/models/user.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/app/core/auth.py`

Tests: `backend/tests/test_api.py`, `backend/tests/test_models.py`, `backend/tests/test_services.py`, `backend/tests/test_auth.py`

### frontend-core — React + TypeScript + Vite Frontend

Status: in_progress

Acceptance:
- Dashboard with cost overview
- Analyze/Waste/Rightsize/Ask/Plan workflows
- Typed API client derived from backend routes
- Loading/error/empty states

### auth-sso — OIDC/Keycloak Authentication with SAML Brokering

Status: planned

Acceptance:
- Keycloak realm import configuration
- Backend session management with HttpOnly cookies
- Frontend PKCE flow with in-memory tokens
- Demo mode for localhost only

### docker-ci — Dockerfiles, Compose, and CI Pipeline

Status: planned

Acceptance:
- Backend and frontend Dockerfiles with non-root users
- compose.yaml with Keycloak and persistent volumes
- GitHub Actions CI running backend/frontend tests and Docker builds

### docs-packaging — Documentation, Packaging, and Portfolio Metadata

Status: planned

Acceptance:
- portfolio.json at root
- CHANGELOG.md with actual changes
- pyproject.toml with author metadata
- README with architecture diagram and API reference
- LICENSE with correct copyright


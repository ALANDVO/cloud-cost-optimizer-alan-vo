# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-13

### Added
- FastAPI backend with create_app factory and lifespan management
- REST API endpoints: `/api/analyze`, `/api/analyses`, `/api/analyses/{id}`, `/api/analyses/{id}/plan`, `/api/analyses/{id}/ask`, `/api/analyses/{id}/rightsize`, `/api/stats`, `/api/health`
- Multi-cloud domain services for AWS (Cost Explorer, CloudWatch, EC2), GCP (Billing, Compute, Monitoring), Azure (Consumption, Compute, Monitor)
- SQLite persistence for Analysis, Recommendation, OptimizationPlan models with UTC timestamps
- LLM service supporting OpenAI-compatible, Anthropic, Gemini, and Ollama providers
- Demo-mode authentication with JWT tokens and CSRF protection (localhost only)
- React + TypeScript + Vite frontend with typed API client
- Dashboard with cost overview cards, provider breakdown, recent analyses
- Analyses list with search, provider filtering, and pagination
- New Analysis form with cloud provider, region, and days selection
- Analysis Detail page with Overview, Waste, Rightsize, Ask Cost AI, and Plan tabs
- Settings page for LLM and cloud provider configuration
- Loading, error, and empty states throughout the UI
- Backend pytest tests (39 tests): API endpoints, domain services, models, authentication
- Frontend Vitest tests (8 tests): Dashboard, Analyses, NewAnalysis, AnalysisDetail components

### Changed
- N/A (initial release)

### Fixed
- N/A (initial release)

### Security
- Demo mode restricted to localhost only; production requires Keycloak OIDC configuration
- JWT tokens signed with configurable secret; HttpOnly SameSite cookies for session management
- CSRF protection on state-changing operations
- No hardcoded secrets; all credentials via environment variables
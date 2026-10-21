# cloud-cost-optimizer-alan-vo — Alan Vo

> Work in progress. This checkpoint may be incomplete or fail tests. See PLAN.md and STATUS.md before use.


> AI-powered cloud cost analysis for AWS, GCP, and Azure — finds waste, right-sizes instances, analyzes spend trends, and generates optimization plans with estimated savings.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-React-3178C6)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)
![SSO](https://img.shields.io/badge/SSO-SAML%20%2F%20OAuth2-8A2BE2)
![License](https://img.shields.io/badge/License-MIT-green)
![AI](https://img.shields.io/badge/AI-Powered-purple)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

</div>

## Why cloud-cost-optimizer-alan-vo?

AI-powered cloud cost analysis for AWS, GCP, and Azure — finds waste, right-sizes instances, analyzes spend trends, and generates optimization plans with estimated savings.

Built by [Alan Vo](https://github.com/ALANDVO) — AI/ML & cybersecurity engineer.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     cloud-cost-optimizer-alan-vo                                    │
├─────────────┬─────────────┬─────────────┬───────────────────┤
│  Frontend   │   API Layer │  Services   │   LLM Engine      │
│  React/TS   │  FastAPI    │  Domain     │  Multi-provider   │
│  Dashboard  │  SSO/SAML   │  Logic      │  OpenAI/Claude/   │
│  Real-time  │  JWT Auth   │  Processing │  Gemini/Ollama    │
└─────────────┴─────────────┴─────────────┴───────────────────┘
         │              │              │               │
         ▼              ▼              ▼               ▼
    ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────────┐
    │ Browser │   │  REST   │   │  Domain │   │  LLM API    │
    │  SPA    │   │  API    │   │  Logic  │   │  (any)      │
    └─────────┘   └─────────┘   └─────────┘   └─────────────┘
```

## Features

- **Multi-cloud cost analysis: AWS Cost Explorer, GCP Billing, Azure Billing APIs**
- **Waste detection: idle EC2 instances, unattached EBS, orphaned IPs, over-provisioned VMs**
- **Right-sizing recommendations using CloudWatch/monitoring utilization data**
- **Reserved instance and committed use discount coverage analysis**
- **Natural language cost questions via LLM integration**
- **Optimization plan generation with monthly savings estimates and prioritized actions**

## Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/ALANDVO/cloud-cost-optimizer-alan-vo.git
cd cloud-cost-optimizer-alan-vo
cp .env.example .env
docker compose up -d
# Open http://localhost:3000
```

### Local Development

```bash
git clone https://github.com/ALANDVO/cloud-cost-optimizer-alan-vo.git
cd cloud-cost-optimizer-alan-vo
pip install -r requirements.txt
```

## Usage

```
python main.py analyze --cloud aws --region us-east-1 --days 30
python main.py waste --cloud aws --region us-east-1
python main.py rightsize --cloud aws --region us-east-1 --instance i-123456
python main.py ask "Where is my biggest waste this month?" --cloud aws
python main.py plan --cloud aws --target-savings 5000
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | LLM API key (OpenAI, Anthropic, Gemini) | Required |
| `LLM_BASE_URL` | Custom LLM endpoint (Ollama, vLLM) | `https://api.openai.com/v1` |
| `LLM_MODEL` | Model name | `gpt-4o` |
| `SAML_IDP_ENTITY` | SAML Identity Provider URL | — |
| `JWT_SECRET` | JWT signing secret | Generate one |

## Tech Stack

`Python` `AWS` `GCP` `Azure` `Cost Optimization` `FinOps` `LLM`

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Login (SSO or email) |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/stats` | Statistics & metrics |
| `POST` | `/api/process` | Main processing endpoint |
| `GET` | `/api/results` | Query results |

## SSO Setup

### SAML
1. Set `SAML_IDP_ENTITY` to your IdP URL
2. Set `SAML_IDP_CERT` to your IdP certificate
3. Set `SAML_ACS_URL` to `https://yourdomain.com/saml/acs`

### OAuth2
1. Register your app with the OAuth provider
2. Set `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET`
3. Set `OAUTH_REDIRECT_URI`

## License

MIT — see [LICENSE](LICENSE)

---

**Built by [Alan Vo](https://github.com/ALANDVO)** | alanvo@gmail.com | AI, ML & Cybersecurity



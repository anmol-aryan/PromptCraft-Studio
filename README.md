# PromptCraft Studio — LLM Prompt Testing Platform

**Built by Anmol Aryan** · BCA Student, JECRC University

PromptCraft Studio is an API-driven workspace for running repeatable zero-shot and few-shot prompt experiments across OpenAI, Anthropic Claude, and a deterministic demo engine. It compares outputs using consistent quality signals and stores every experiment for later review.

## Features

- Side-by-side multi-provider prompt execution
- Zero-shot and few-shot experiment modes
- Automatic scoring for keyword coverage, clarity, format adherence, and conciseness
- Latency and token-usage comparison
- SQLite-backed experiment history
- JSON export for reproducible evaluations
- Safe demo mode that works without API keys
- Responsive interface and keyboard shortcut (`Cmd/Ctrl + Enter`)
- Interactive FastAPI documentation at `/docs`

## Tech stack

- **Backend:** Python, FastAPI, Pydantic
- **LLM providers:** OpenAI Responses API, Anthropic Messages API
- **Database:** SQLite
- **Frontend:** HTML, CSS, JavaScript
- **Testing:** Pytest, FastAPI TestClient
- **Deployment:** Docker and Render configuration included

## Local setup

Requirements: Python 3.11+

```bash
git clone <your-repository-url>
cd promptcraft-studio
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`. The application works immediately in demo mode.

## Optional API configuration

Add provider keys only to your local `.env` file or deployment environment:

```env
OPENAI_API_KEY=your_private_key
ANTHROPIC_API_KEY=your_private_key
```

Never commit `.env` or expose API keys in frontend code.

## Run tests

```bash
pytest -q
```

## API example

```bash
curl -X POST http://127.0.0.1:8000/api/compare \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Summarize the benefits of prompt testing.",
    "providers": [{"provider": "demo", "model": "promptcraft-demo"}],
    "expected_keywords": ["accuracy", "consistency"]
  }'
```

## How it works

1. The API validates a shared prompt configuration.
2. Selected providers run concurrently to reduce comparison time.
3. Every output is evaluated with the same deterministic scoring rules.
4. Results and request settings are stored in SQLite.
5. The interface highlights the strongest score and supports JSON export.

## Interview explanation

“PromptCraft Studio turns prompt engineering into a repeatable experiment instead of trial and error. A single validated request is executed concurrently across selected LLM providers. The platform records latency and token usage, then applies the same deterministic evaluation rubric to every output. Experiments are persisted so prompt versions can be compared and reproduced. Provider failures fall back safely to a demo engine, so the full workflow remains testable without exposing API keys.”

## Resume bullets

- Built a Python and FastAPI platform to compare zero-shot and few-shot prompts across OpenAI and Anthropic Claude APIs.
- Implemented concurrent provider execution, deterministic output scoring, token and latency tracking, and SQLite experiment history.
- Added secure environment-based API configuration, demo fallbacks, JSON exports, automated API tests, and Docker-ready deployment.

## API documentation

- Swagger UI: `/docs`
- OpenAPI schema: `/openapi.json`


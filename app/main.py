from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import delete_experiment, get_experiment, initialize_database, list_experiments, save_experiment
from .evaluation import score_output
from .models import ComparisonRequest, ComparisonResponse, ProviderResult
from .providers import run_provider


ROOT = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="PromptCraft Studio API",
    description="Compare zero-shot and few-shot prompts across multiple LLM providers.",
    version="1.0.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "promptcraft-studio"}


@app.post("/api/compare", response_model=ComparisonResponse)
async def compare_prompts(request: ComparisonRequest) -> ComparisonResponse:
    raw_results = await asyncio.gather(*(run_provider(provider, request) for provider in request.providers))
    results: list[ProviderResult] = []
    for config, raw in zip(request.providers, raw_results, strict=True):
        results.append(
            ProviderResult(
                provider=config.provider,
                model=config.model,
                output=raw.output,
                latency_ms=raw.latency_ms,
                input_tokens=raw.input_tokens,
                output_tokens=raw.output_tokens,
                scores=score_output(request.prompt, raw.output, request.expected_keywords),
                status=raw.status,
                error=raw.error,
            )
        )

    successful = [result for result in results if result.status != "error"]
    winner = max(successful, key=lambda result: result.scores.overall).provider if successful else None
    created_at = datetime.now(timezone.utc).isoformat()
    response = ComparisonResponse(
        experiment_id=f"exp_{uuid.uuid4().hex[:10]}",
        created_at=created_at,
        experiment_type=request.experiment_type,
        winner=winner,
        results=results,
    )
    save_experiment(response.experiment_id, created_at, request.model_dump(), response.model_dump())
    return response


@app.get("/api/experiments")
async def experiments(limit: int = Query(default=20, ge=1, le=100)):
    return {"experiments": list_experiments(limit)}


@app.get("/api/experiments/{experiment_id}")
async def experiment(experiment_id: str):
    item = get_experiment(experiment_id)
    if not item:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return item


@app.delete("/api/experiments/{experiment_id}", status_code=204)
async def remove_experiment(experiment_id: str):
    if not delete_experiment(experiment_id):
        raise HTTPException(status_code=404, detail="Experiment not found")


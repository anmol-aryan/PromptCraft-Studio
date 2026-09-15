from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


ProviderName = Literal["demo", "openai", "anthropic"]


class FewShotExample(BaseModel):
    input: str = Field(min_length=1, max_length=4_000)
    output: str = Field(min_length=1, max_length=4_000)


class ProviderConfig(BaseModel):
    provider: ProviderName
    model: str = Field(min_length=1, max_length=120)


class ComparisonRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=20_000)
    system_prompt: str = Field(default="You are a helpful, accurate assistant.", max_length=8_000)
    experiment_type: Literal["zero-shot", "few-shot"] = "zero-shot"
    examples: list[FewShotExample] = Field(default_factory=list, max_length=8)
    providers: list[ProviderConfig] = Field(
        default_factory=lambda: [ProviderConfig(provider="demo", model="promptcraft-demo")],
        min_length=1,
        max_length=3,
    )
    expected_keywords: list[str] = Field(default_factory=list, max_length=20)
    temperature: float = Field(default=0.3, ge=0, le=1)
    max_tokens: int = Field(default=500, ge=32, le=4_000)

    @field_validator("expected_keywords")
    @classmethod
    def clean_keywords(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            keyword = value.strip().lower()
            if keyword and keyword not in cleaned:
                cleaned.append(keyword)
        return cleaned

    @field_validator("examples")
    @classmethod
    def require_examples_for_few_shot(cls, values: list[FewShotExample], info):
        if info.data.get("experiment_type") == "few-shot" and not values:
            raise ValueError("Few-shot experiments require at least one example")
        return values


class ScoreBreakdown(BaseModel):
    keyword_coverage: float
    clarity: float
    format_adherence: float
    conciseness: float
    overall: float


class ProviderResult(BaseModel):
    provider: ProviderName
    model: str
    output: str
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    scores: ScoreBreakdown
    status: Literal["success", "fallback", "error"]
    error: str | None = None


class ComparisonResponse(BaseModel):
    experiment_id: str
    created_at: str
    experiment_type: str
    winner: str | None
    results: list[ProviderResult]


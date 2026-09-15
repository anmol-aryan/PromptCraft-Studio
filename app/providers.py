from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

from .models import ComparisonRequest, ProviderConfig


@dataclass
class RawProviderResult:
    output: str
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    status: str = "success"
    error: str | None = None


def _compose_prompt(request: ComparisonRequest) -> str:
    parts = [request.system_prompt.strip()]
    if request.experiment_type == "few-shot" and request.examples:
        parts.append("\nExamples:")
        for index, example in enumerate(request.examples, 1):
            parts.append(f"Example {index}\nInput: {example.input}\nOutput: {example.output}")
    parts.append(f"\nTask:\n{request.prompt.strip()}")
    return "\n\n".join(parts)


def _demo_response(request: ComparisonRequest, model: str) -> RawProviderResult:
    started = time.perf_counter()
    prompt = request.prompt.strip()
    lowered = prompt.lower()
    keywords = request.expected_keywords or ["clear", "accurate", "actionable"]

    if "json" in lowered:
        output = json.dumps(
            {
                "result": "Prompt evaluated successfully in deterministic demo mode.",
                "method": request.experiment_type,
                "key_points": keywords[:4],
                "recommendation": "Add a precise audience, output format, and evaluation criteria.",
            },
            indent=2,
        )
    elif "classif" in lowered or "sentiment" in lowered:
        output = (
            "Classification: Positive\n"
            "Confidence: 0.91\n"
            "Reason: The message contains clear satisfaction and recommendation signals."
        )
    elif "summar" in lowered:
        output = (
            "Summary: A strong prompt defines the role, task, context, constraints, and expected output. "
            "Testing the same prompt across models reveals trade-offs in accuracy, clarity, latency, and cost."
        )
    else:
        output = (
            f"Here is a structured response for the requested task: {prompt[:180]}\n\n"
            "1. Define the intended outcome and audience.\n"
            "2. Supply only the context needed to complete the task accurately.\n"
            "3. Specify constraints and a clear output format.\n"
            f"4. Validate the result for {', '.join(keywords[:3])}.\n\n"
            "This demo output is deterministic, so the complete comparison workflow can be tested without an API key."
        )

    latency = max(35, int((time.perf_counter() - started) * 1000) + 80)
    return RawProviderResult(
        output=output,
        latency_ms=latency,
        input_tokens=max(1, len(_compose_prompt(request)) // 4),
        output_tokens=max(1, len(output) // 4),
        status="fallback",
    )


async def run_provider(config: ProviderConfig, request: ComparisonRequest) -> RawProviderResult:
    if config.provider == "demo":
        return _demo_response(request, config.model)

    prompt = _compose_prompt(request)
    started = time.perf_counter()

    try:
        if config.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                result = _demo_response(request, config.model)
                result.error = "OPENAI_API_KEY is not configured; demo output used."
                return result
            from openai import AsyncOpenAI

            response = await AsyncOpenAI(api_key=api_key).responses.create(
                model=config.model,
                input=prompt,
                temperature=request.temperature,
                max_output_tokens=request.max_tokens,
            )
            usage = getattr(response, "usage", None)
            return RawProviderResult(
                output=response.output_text,
                latency_ms=int((time.perf_counter() - started) * 1000),
                input_tokens=getattr(usage, "input_tokens", None),
                output_tokens=getattr(usage, "output_tokens", None),
            )

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            result = _demo_response(request, config.model)
            result.error = "ANTHROPIC_API_KEY is not configured; demo output used."
            return result
        from anthropic import AsyncAnthropic

        response = await AsyncAnthropic(api_key=api_key).messages.create(
            model=config.model,
            max_tokens=request.max_tokens,
            system=request.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        output = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        return RawProviderResult(
            output=output,
            latency_ms=int((time.perf_counter() - started) * 1000),
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
    except Exception as exc:  # Provider failures should not break the comparison.
        fallback = _demo_response(request, config.model)
        fallback.error = f"Provider request failed; demo output used: {str(exc)[:180]}"
        return fallback


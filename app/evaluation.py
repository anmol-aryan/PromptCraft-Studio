from __future__ import annotations

import json
import re

from .models import ScoreBreakdown


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def score_output(prompt: str, output: str, expected_keywords: list[str]) -> ScoreBreakdown:
    lowered = output.lower()
    words = re.findall(r"\b[\w'-]+\b", output)
    sentences = [s for s in re.split(r"[.!?]+", output) if s.strip()]

    if expected_keywords:
        matched = sum(1 for keyword in expected_keywords if keyword in lowered)
        keyword_coverage = 100 * matched / len(expected_keywords)
    else:
        keyword_coverage = 100.0

    average_sentence = len(words) / max(1, len(sentences))
    clarity = 94 - abs(average_sentence - 16) * 1.5
    if len(output.strip()) < 30:
        clarity -= 25

    asks_for_json = "json" in prompt.lower()
    if asks_for_json:
        try:
            json.loads(output.strip().removeprefix("```json").removesuffix("```").strip())
            format_adherence = 100.0
        except (json.JSONDecodeError, TypeError):
            format_adherence = 25.0
    else:
        format_adherence = 100.0

    word_count = len(words)
    if word_count <= 180:
        conciseness = 100.0
    else:
        conciseness = 100 - (word_count - 180) * 0.18

    keyword_coverage = _clamp(keyword_coverage)
    clarity = _clamp(clarity)
    format_adherence = _clamp(format_adherence)
    conciseness = _clamp(conciseness)
    overall = _clamp(
        keyword_coverage * 0.35
        + clarity * 0.25
        + format_adherence * 0.25
        + conciseness * 0.15
    )
    return ScoreBreakdown(
        keyword_coverage=keyword_coverage,
        clarity=clarity,
        format_adherence=format_adherence,
        conciseness=conciseness,
        overall=overall,
    )


from dataclasses import dataclass

from .config import Settings


@dataclass(frozen=True, slots=True)
class UsageMetrics:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0


def estimate_cost_usd(usage: UsageMetrics, settings: Settings) -> float | None:
    """Estimate cost only when all relevant current rates are configured."""

    input_rate = settings.openai_input_usd_per_million
    output_rate = settings.openai_output_usd_per_million
    cached_rate = settings.openai_cached_input_usd_per_million
    if input_rate is None or output_rate is None:
        return None

    cached_rate = input_rate if cached_rate is None else cached_rate
    uncached_input = max(usage.input_tokens - usage.cached_input_tokens, 0)
    total = (
        uncached_input * input_rate
        + usage.cached_input_tokens * cached_rate
        + usage.output_tokens * output_rate
    ) / 1_000_000
    return round(total, 8)

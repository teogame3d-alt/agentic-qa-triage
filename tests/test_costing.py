from agentic_qa_triage.config import Settings
from agentic_qa_triage.costing import UsageMetrics, estimate_cost_usd


def test_cost_is_not_invented_when_rates_are_missing() -> None:
    settings = Settings(database_url="sqlite+pysqlite:///:memory:")
    usage = UsageMetrics(input_tokens=1_000, output_tokens=200)

    assert estimate_cost_usd(usage, settings) is None


def test_cost_separates_cached_and_uncached_input() -> None:
    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        openai_input_usd_per_million=2.0,
        openai_cached_input_usd_per_million=0.5,
        openai_output_usd_per_million=8.0,
    )
    usage = UsageMetrics(
        input_tokens=1_000,
        cached_input_tokens=400,
        output_tokens=200,
    )

    assert estimate_cost_usd(usage, settings) == 0.003

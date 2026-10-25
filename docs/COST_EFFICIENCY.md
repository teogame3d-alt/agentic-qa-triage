# Cost-Efficiency Strategy

Cost efficiency is part of the application contract, not a README claim.

## Implemented controls

- Demo provider exercises the complete UI, storage, and approval workflow at zero API cost.
- OpenAI runs have a configurable maximum turn count.
- Incident input has a strict character budget.
- The model returns a typed compact object with a bounded output-token budget.
- There is one focused agent and one read-only tool instead of a default multi-agent graph.
- Every run records input, cached input, and output tokens.
- USD estimates are calculated only when current rates are explicitly configured.
- Stable instructions appear before incident data, which makes the prompt friendlier to caching.

## Why prices are not hardcoded

API prices change. Stale prices produce misleading portfolio dashboards, so this project accepts
the current price per million tokens through environment variables. If rates are absent, the UI
shows token counts and `Not priced` instead of inventing a number.

## Evaluation plan

Use a small reviewed dataset of incident reports and compare:

1. correct severity and category;
2. unsupported claims in the summary;
3. useful reproduction and test steps;
4. average tokens and latency per accepted draft;
5. approval rate and edits required before approval.

Only introduce a second agent or a larger model when those measurements identify a quality gap.

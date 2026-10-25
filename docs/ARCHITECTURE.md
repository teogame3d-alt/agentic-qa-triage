# Architecture

## Runtime boundary

```text
Browser dashboard
       |
       v
FastAPI validation -----> SQLite (zero-setup demo)
       |                  PostgreSQL (Docker/deploy path)
       v
TriageService
       |
       +---- demo provider (deterministic, zero API cost)
       |
       +---- OpenAI Agents SDK
                 |
                 +---- read-only knowledge-base tool
                 +---- typed TriageDecision output
       |
       v
Draft incident -----> explicit human approval endpoint
```

Application code owns input limits, database writes, approval state, token accounting, and the
maximum number of agent turns. The agent owns only the bounded triage decision and a read-only
retrieval choice.

## Why one agent

The MVP uses one focused specialist because the task has one clear owner. Adding a manager and
multiple specialists would create extra calls, latency, and failure modes without proving more
value. A second specialist is justified only when evaluation shows that reproduction planning or
security classification needs a genuinely different prompt and tool set.

## Data model

- `incidents`: user evidence, proposed decision, confidence, and approval state.
- `agent_runs`: provider, model, latency, tool calls, token usage, and optional estimated cost.
- `known_incidents`: reviewed examples available through the read-only retrieval tool.

## Safety decisions

- Model output is validated as `TriageDecision` before persistence.
- User input is length-limited and described to the model as untrusted evidence.
- The only agent tool is read-only.
- Approval is an application endpoint, not an agent tool.
- API keys and `.env` files are ignored by Git.
- Model response storage is disabled in the SDK configuration.

## Known limitations

- The compact keyword retrieval is intentionally deterministic; production search could use
  PostgreSQL full-text search or embeddings after evaluation.
- `create_all()` is sufficient for this MVP. A deployed evolving schema should add Alembic.
- Authentication and role-based approval are outside the public portfolio scope.

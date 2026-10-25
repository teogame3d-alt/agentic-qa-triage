# Interview Guide

## Thirty-second explanation

Agentic QA Triage turns an unstructured incident report into a reviewable QA draft. A Python agent
can search previously reviewed incidents, then returns a typed severity, summary, reproduction
plan, and test plan. FastAPI and PostgreSQL own persistence, every run records usage, and a human
must approve the result.

## Engineering decisions to explain

- **Why an agent?** Retrieval is optional and chosen from report content; the workflow can take
  multiple model/tool steps rather than producing one blind completion.
- **Why not many agents?** One specialist is cheaper and easier to evaluate for this bounded task.
- **Why PostgreSQL?** Incidents, approvals, and usage records are relational and need reliable
  querying. SQLite keeps local review friction low.
- **Why typed output?** The API never stores an arbitrary paragraph as a decision.
- **Why human approval?** Severity affects prioritization, so the model drafts but does not accept.
- **How is cost controlled?** Bounded context, bounded turns, compact output, measured tokens, and
  no hardcoded pricing.

## Be ready to demonstrate

1. Run the app in demo mode and submit the included login-loop sample.
2. Explain the read-only knowledge-base tool and show the matched incident ID.
3. Show that the result stays in `draft` until the separate approval action.
4. Point to the agent-run usage record and pricing configuration.
5. Run the automated tests.

## Honest scope

This is a portfolio MVP, not an autonomous production incident-management platform. A production
version still needs authentication, role-based access, schema migrations, deployment monitoring,
and an evaluated incident dataset.

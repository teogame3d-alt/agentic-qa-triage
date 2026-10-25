const elements = {
  form: document.querySelector("#triage-form"),
  submit: document.querySelector("#submit-button"),
  message: document.querySelector("#form-message"),
  list: document.querySelector("#incident-list"),
  empty: document.querySelector("#empty-state"),
  runtime: document.querySelector("#runtime span:last-child"),
};

const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = Array.isArray(payload.detail)
      ? payload.detail.map((item) => item.msg).join("; ")
      : payload.detail;
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return response.json();
}

function listItems(items) {
  if (!items?.length) return "<li>No additional items</li>";
  return items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderIncident(incident) {
  const run = incident.runs?.[0];
  const tokens = run ? run.input_tokens + run.output_tokens : 0;
  const cost = run?.estimated_cost_usd == null ? "Not priced" : `$${run.estimated_cost_usd.toFixed(6)}`;
  const approval =
    incident.status === "approved"
      ? '<div class="approved-label">✓ Human approved</div>'
      : `<button class="approve-button" data-approve="${incident.id}">Approve draft</button>`;
  return `
    <article class="incident-card">
      <div>
        <div class="incident-topline">
          <span class="incident-id">INC-${String(incident.id).padStart(3, "0")}</span>
          <span class="tag ${escapeHtml(incident.severity)}">${escapeHtml(incident.severity)}</span>
          <span class="tag">${escapeHtml(incident.category)}</span>
          <span class="tag ${escapeHtml(incident.status)}">${escapeHtml(incident.status)}</span>
        </div>
        <h3>${escapeHtml(incident.title)}</h3>
        <p class="incident-summary">${escapeHtml(incident.summary)}</p>
        <div class="detail-grid">
          <div>
            <h4>REPRODUCTION</h4>
            <ul>${listItems(incident.reproduction_steps)}</ul>
          </div>
          <div>
            <h4>TEST PLAN</h4>
            <ul>${listItems(incident.test_plan)}</ul>
          </div>
        </div>
      </div>
      <aside class="run-box">
        <h4>CONFIDENCE</h4>
        <div class="confidence">${Math.round((incident.confidence || 0) * 100)}%</div>
        <div class="run-stats">
          <div>Provider<strong>${escapeHtml(run?.provider || incident.source)}</strong></div>
          <div>Tool calls<strong>${run?.tool_calls ?? 0}</strong></div>
          <div>Tokens<strong>${tokens.toLocaleString()}</strong></div>
          <div>Est. cost<strong>${escapeHtml(cost)}</strong></div>
          <div>Latency<strong>${run?.duration_ms ?? 0} ms</strong></div>
          <div>Similar IDs<strong>${incident.similar_incident_ids.join(", ") || "None"}</strong></div>
        </div>
        ${approval}
      </aside>
    </article>`;
}

async function loadRuntime() {
  const health = await request("/health");
  elements.runtime.textContent = `${health.provider} · ${health.model} · ${health.database}`;
}

async function loadMetrics() {
  const metrics = await request("/api/metrics");
  document.querySelector("#metric-incidents").textContent = metrics.incidents.toLocaleString();
  document.querySelector("#metric-approved").textContent = `${metrics.approved_incidents} human-approved`;
  document.querySelector("#metric-runs").textContent = metrics.runs.toLocaleString();
  const providers = Object.entries(metrics.provider_breakdown)
    .map(([name, count]) => `${name}: ${count}`)
    .join(" · ");
  document.querySelector("#metric-provider").textContent = providers || "No provider activity";
  document.querySelector("#metric-tokens").textContent = (
    metrics.input_tokens + metrics.output_tokens
  ).toLocaleString();
  document.querySelector("#metric-cached").textContent = `${metrics.cached_input_tokens.toLocaleString()} cached input tokens`;
  document.querySelector("#metric-cost").textContent =
    metrics.estimated_cost_usd == null ? "—" : `$${metrics.estimated_cost_usd.toFixed(6)}`;
}

async function loadIncidents() {
  const incidents = await request("/api/incidents?limit=30");
  elements.empty.hidden = incidents.length > 0;
  elements.list.innerHTML = incidents.map(renderIncident).join("");
}

async function refresh() {
  await Promise.all([loadRuntime(), loadMetrics(), loadIncidents()]);
}

elements.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  elements.submit.disabled = true;
  elements.submit.textContent = "Running bounded workflow…";
  elements.message.className = "form-message";
  elements.message.textContent = "Validating evidence and preparing the draft.";
  try {
    await request("/api/incidents/triage", {
      method: "POST",
      body: JSON.stringify({
        title: document.querySelector("#title").value,
        description: document.querySelector("#description").value,
        environment: document.querySelector("#environment").value || "Not provided",
        reporter: document.querySelector("#reporter").value || "Portfolio demo",
      }),
    });
    elements.message.textContent = "Draft created. Review it before approval.";
    await Promise.all([loadMetrics(), loadIncidents()]);
    document.querySelector(".results-section").scrollIntoView({ behavior: "smooth" });
  } catch (error) {
    elements.message.className = "form-message error";
    elements.message.textContent = error.message;
  } finally {
    elements.submit.disabled = false;
    elements.submit.textContent = "Run triage workflow";
  }
});

elements.list.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-approve]");
  if (!button) return;
  button.disabled = true;
  button.textContent = "Approving…";
  try {
    await request(`/api/incidents/${button.dataset.approve}/approve`, { method: "POST" });
    await Promise.all([loadMetrics(), loadIncidents()]);
  } catch (error) {
    button.disabled = false;
    button.textContent = error.message;
  }
});

document.querySelector("#sample-button").addEventListener("click", () => {
  document.querySelector("#title").value = "Users enter a redirect loop after session expiry";
  document.querySelector("#description").value =
    "On staging, an expired user session causes repeated redirects between /login and /dashboard. " +
    "The API returns 401 on every refresh. Expected: one refresh attempt, followed by a clear login screen. " +
    "The issue happens every time after leaving the tab open for 30 minutes.";
  document.querySelector("#environment").value = "Windows 11, Chrome, staging build 0.9.4";
});

document.querySelector("#refresh-button").addEventListener("click", refresh);

refresh().catch((error) => {
  elements.runtime.textContent = "Runtime unavailable";
  elements.message.className = "form-message error";
  elements.message.textContent = error.message;
});

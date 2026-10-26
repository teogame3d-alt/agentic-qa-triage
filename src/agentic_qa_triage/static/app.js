const elements = {
  form: document.querySelector("#triage-form"),
  submit: document.querySelector("#submit-button"),
  message: document.querySelector("#form-message"),
  list: document.querySelector("#incident-list"),
  empty: document.querySelector("#empty-state"),
  runtime: document.querySelector("#runtime span:last-child"),
  title: document.querySelector("#title"),
  description: document.querySelector("#description"),
  titleCount: document.querySelector("#title-count"),
  descriptionCount: document.querySelector("#description-count"),
  latencyChart: document.querySelector("#latency-chart"),
  approvalDonut: document.querySelector("#approval-donut"),
  approvalDonutValue: document.querySelector("#approval-donut-value"),
  approvalDonutLabel: document.querySelector("#approval-donut-label"),
  healthCompletion: document.querySelector("#health-completion"),
  healthStatus: document.querySelector("#health-status"),
};

const REQUEST_TIMEOUT_MS = 20_000;
let latestMetrics = null;
let latestIncidents = [];

const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(path, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      signal: controller.signal,
    });
    const raw = await response.text();
    let payload = {};
    try {
      payload = raw ? JSON.parse(raw) : {};
    } catch {
      payload = {};
    }
    if (!response.ok) {
      const detail = Array.isArray(payload.detail)
        ? payload.detail.map((item) => item.msg).join("; ")
        : payload.detail;
      throw new Error(detail || `Request failed with status ${response.status}`);
    }
    return payload;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("The request timed out. No result was accepted; please try again.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

function updateCounters() {
  elements.titleCount.textContent = `${elements.title.value.length.toLocaleString()} / 200`;
  elements.descriptionCount.textContent = `${elements.description.value.length.toLocaleString()} / 10,000`;
}

function listItems(items) {
  if (!items?.length) return "<li>No additional items</li>";
  return items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderLatencyChart(incidents) {
  const completed = incidents
    .filter((incident) => incident.runs?.[0])
    .slice(0, 8)
    .reverse();
  if (!completed.length) {
    elements.latencyChart.innerHTML = '<span class="chart-empty">Awaiting the first completed case</span>';
    return;
  }
  const durations = completed.map((incident) => incident.runs[0].duration_ms || 0);
  const maxDuration = Math.max(...durations, 1);
  elements.latencyChart.innerHTML = completed
    .map((incident, index) => {
      const duration = incident.runs[0].duration_ms || 0;
      const height = Math.max(14, Math.round((duration / maxDuration) * 100));
      return `<div class="chart-bar-group" title="${escapeHtml(incident.title)}">
        <div class="chart-bar" style="height: ${height}%"></div>
        <span>${String(index + 1).padStart(2, "0")}</span>
      </div>`;
    })
    .join("");
}

function renderOperationalStats() {
  if (!latestMetrics) return;
  const approvalPercent = Math.round(latestMetrics.approval_rate * 100);
  elements.approvalDonut.style.setProperty("--approval-angle", `${approvalPercent * 3.6}deg`);
  elements.approvalDonutValue.textContent = `${approvalPercent}%`;
  elements.approvalDonutLabel.textContent = latestMetrics.incidents
    ? `${latestMetrics.approved_incidents} of ${latestMetrics.incidents} cases approved`
    : "Waiting for activity";
  elements.healthCompletion.textContent = `${Math.round(latestMetrics.completion_rate * 100)}%`;
  renderLatencyChart(latestIncidents);
}

function renderIncident(incident) {
  const run = incident.runs?.[0];
  const approval =
    incident.status === "approved"
      ? '<div class="approved-label">✓ Human approved</div>'
      : `<button class="approve-button" data-approve="${incident.id}">Approve after review</button>`;
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
          <div>Response time<strong>${run?.duration_ms ?? 0} ms</strong></div>
          <div>Related cases<strong>${incident.similar_incident_ids.length || "None"}</strong></div>
        </div>
        ${approval}
      </aside>
    </article>`;
}

async function loadRuntime() {
  const health = await request("/health");
  const ready = health.status === "ok";
  elements.runtime.textContent = ready ? "Service ready" : "Service unavailable";
  elements.healthStatus.textContent = ready ? "Ready" : "Unavailable";
  elements.healthStatus.className = ready ? "status-ready" : "status-error";
}

async function loadMetrics() {
  const metrics = await request("/api/metrics");
  latestMetrics = metrics;
  document.querySelector("#metric-incidents").textContent = metrics.incidents.toLocaleString();
  document.querySelector("#metric-approved-count").textContent = `${metrics.approved_incidents.toLocaleString()} approved`;
  document.querySelector("#metric-runs").textContent = metrics.runs.toLocaleString();
  document.querySelector("#metric-completion-rate").textContent = `${Math.round(metrics.completion_rate * 100)}% completion`;
  document.querySelector("#metric-approval-rate").textContent = `${Math.round(metrics.approval_rate * 100)}%`;
  document.querySelector("#metric-latency").textContent =
    metrics.average_latency_ms == null ? "—" : `${Math.round(metrics.average_latency_ms)} ms`;
  document.querySelector("#metric-last-activity").textContent = metrics.last_activity_at
    ? `Last activity ${new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(metrics.last_activity_at))}`
    : "Waiting for activity";
  renderOperationalStats();
}

async function loadIncidents() {
  const incidents = await request("/api/incidents?limit=30");
  latestIncidents = incidents;
  elements.empty.hidden = incidents.length > 0;
  elements.list.innerHTML = incidents.map(renderIncident).join("");
  renderOperationalStats();
}

async function refresh() {
  await Promise.all([loadRuntime(), loadMetrics(), loadIncidents()]);
}

elements.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!elements.form.reportValidity()) return;
  const title = elements.title.value.trim();
  const description = elements.description.value.trim();
  if (title.length < 5 || description.length < 20) {
    elements.message.className = "form-message error";
    elements.message.textContent = "Add a title of at least 5 characters and evidence of at least 20 characters.";
    return;
  }
  elements.submit.disabled = true;
  elements.form.setAttribute("aria-busy", "true");
  elements.submit.textContent = "Preparing QA draft…";
  elements.message.className = "form-message";
  elements.message.textContent = "Validating evidence and preparing the draft.";
  try {
    await request("/api/incidents/triage", {
      method: "POST",
      body: JSON.stringify({
        title,
        description,
        environment: document.querySelector("#environment").value.trim() || "Not provided",
        reporter: document.querySelector("#reporter").value.trim() || "Unspecified",
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
    elements.form.removeAttribute("aria-busy");
    elements.submit.textContent = "Create QA draft";
  }
});

elements.list.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-approve]");
  if (!button) return;
  if (button.dataset.busy === "true") return;
  if (!window.confirm("Approve this QA draft? This marks the recommendation as human-approved.")) {
    return;
  }
  button.dataset.busy = "true";
  button.disabled = true;
  button.textContent = "Approving…";
  try {
    await request(`/api/incidents/${button.dataset.approve}/approve`, { method: "POST" });
    await Promise.all([loadMetrics(), loadIncidents()]);
  } catch (error) {
    delete button.dataset.busy;
    button.disabled = false;
    button.textContent = "Approve after review";
    elements.message.className = "form-message error";
    elements.message.textContent = error.message;
  }
});

document.querySelector("#refresh-button").addEventListener("click", refresh);
elements.title.addEventListener("input", updateCounters);
elements.description.addEventListener("input", updateCounters);
updateCounters();

refresh().catch((error) => {
  elements.runtime.textContent = "Runtime unavailable";
  elements.message.className = "form-message error";
  elements.message.textContent = error.message;
});

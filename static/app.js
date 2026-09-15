const state = { mode: "zero-shot", latest: null };

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const promptInput = $("#prompt");
const runButton = $("#runButton");
const resultGrid = $("#resultGrid");
const emptyState = $("#emptyState");
const errorMessage = $("#errorMessage");

function updateCharacterCount() {
  $("#charCount").textContent = `${promptInput.value.length.toLocaleString()} / 20,000`;
}

function selectedProviders() {
  const modelMap = { demo: "promptcraft-demo", openai: "gpt-5-mini", anthropic: "claude-sonnet-4-5" };
  return $$(".provider-card input:checked").map((input) => ({ provider: input.value, model: modelMap[input.value] }));
}

function buildPayload() {
  const examples = state.mode === "few-shot"
    ? [{ input: $("#exampleInput").value.trim(), output: $("#exampleOutput").value.trim() }]
    : [];
  return {
    prompt: promptInput.value.trim(),
    system_prompt: $("#systemPrompt").value.trim(),
    experiment_type: state.mode,
    examples,
    providers: selectedProviders(),
    expected_keywords: $("#keywords").value.split(",").map((value) => value.trim()).filter(Boolean),
    temperature: Number($("#temperature").value),
    max_tokens: 500,
  };
}

function escapeHtml(value) {
  return value.replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#039;", '"': "&quot;" })[char]);
}

function resultCard(result, winner) {
  const isWinner = result.provider === winner;
  return `<article class="result-card ${isWinner ? "winner" : ""}">
    <div class="result-top">
      <div class="model-name"><span class="provider-icon ${result.provider === "anthropic" ? "claude-icon" : result.provider === "openai" ? "openai-icon" : "demo-icon"}">${result.provider[0].toUpperCase()}</span><span><strong>${escapeHtml(result.provider)}</strong><small>${escapeHtml(result.model)}</small></span></div>
      ${isWinner ? '<span class="winner-badge">Best score</span>' : ""}
    </div>
    <pre class="output">${escapeHtml(result.output)}</pre>
    <div class="metrics">
      <div class="metric overall"><small>Overall</small><strong>${result.scores.overall}</strong></div>
      <div class="metric"><small>Keywords</small><strong>${result.scores.keyword_coverage}%</strong></div>
      <div class="metric"><small>Clarity</small><strong>${result.scores.clarity}</strong></div>
      <div class="metric"><small>Latency</small><strong>${result.latency_ms}ms</strong></div>
      <div class="metric"><small>Tokens</small><strong>${result.output_tokens ?? "—"}</strong></div>
    </div>
    ${result.error ? `<div class="fallback-note">${escapeHtml(result.error)}</div>` : ""}
  </article>`;
}

function renderResults(data) {
  state.latest = data;
  emptyState.hidden = true;
  resultGrid.hidden = false;
  resultGrid.innerHTML = data.results.map((result) => resultCard(result, data.winner)).join("");
  $("#exportButton").disabled = false;
}

async function runExperiment() {
  errorMessage.textContent = "";
  const payload = buildPayload();
  if (payload.prompt.length < 3) return (errorMessage.textContent = "Enter a prompt with at least three characters.");
  if (!payload.providers.length) return (errorMessage.textContent = "Select at least one provider.");
  if (state.mode === "few-shot" && (!payload.examples[0].input || !payload.examples[0].output)) return (errorMessage.textContent = "Complete both few-shot example fields.");

  runButton.disabled = true;
  runButton.querySelector("span").textContent = "Running experiment…";
  try {
    const response = await fetch("/api/compare", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!response.ok) throw new Error((await response.json()).detail || "Comparison failed");
    renderResults(await response.json());
    await loadHistory();
  } catch (error) {
    errorMessage.textContent = error.message;
  } finally {
    runButton.disabled = false;
    runButton.querySelector("span").textContent = "Run comparison";
  }
}

async function loadHistory() {
  try {
    const response = await fetch("/api/experiments?limit=30");
    const data = await response.json();
    $("#historyCount").textContent = data.experiments.length;
    $("#historyList").innerHTML = data.experiments.length
      ? data.experiments.map((item) => `<div class="history-item" data-id="${item.id}"><strong>${escapeHtml(item.prompt)}</strong><span>${item.experiment_type} · ${new Date(item.created_at).toLocaleString()} · winner: ${item.winner || "—"}</span></div>`).join("")
      : '<p class="hint">No saved experiments yet.</p>';
    $$(".history-item").forEach((item) => item.addEventListener("click", () => restoreExperiment(item.dataset.id)));
  } catch (_) { /* History is non-blocking. */ }
}

async function restoreExperiment(id) {
  const response = await fetch(`/api/experiments/${id}`);
  if (!response.ok) return;
  const data = await response.json();
  promptInput.value = data.request.prompt;
  $("#systemPrompt").value = data.request.system_prompt;
  $("#keywords").value = data.request.expected_keywords.join(", ");
  setMode(data.request.experiment_type);
  renderResults(data.response);
  closeHistory();
  updateCharacterCount();
}

function setMode(mode) {
  state.mode = mode;
  $$(".segmented button").forEach((button) => button.classList.toggle("active", button.dataset.mode === mode));
  $("#examplesPanel").hidden = mode !== "few-shot";
}

function openHistory() {
  $("#historyDrawer").classList.add("open");
  $("#historyDrawer").setAttribute("aria-hidden", "false");
  $("#backdrop").hidden = false;
}
function closeHistory() {
  $("#historyDrawer").classList.remove("open");
  $("#historyDrawer").setAttribute("aria-hidden", "true");
  $("#backdrop").hidden = true;
}

promptInput.addEventListener("input", updateCharacterCount);
$("#temperature").addEventListener("input", (event) => $("#temperatureValue").textContent = event.target.value);
$$(".segmented button").forEach((button) => button.addEventListener("click", () => setMode(button.dataset.mode)));
$$(".provider-card input").forEach((input) => input.addEventListener("change", () => input.closest(".provider-card").classList.toggle("selected", input.checked)));
runButton.addEventListener("click", runExperiment);
$("#historyButton").addEventListener("click", openHistory);
$("#closeHistory").addEventListener("click", closeHistory);
$("#backdrop").addEventListener("click", closeHistory);
$("#exportButton").addEventListener("click", () => {
  if (!state.latest) return;
  const blob = new Blob([JSON.stringify(state.latest, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${state.latest.experiment_id}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
});
document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") runExperiment();
  if (event.key === "Escape") closeHistory();
});

updateCharacterCount();
loadHistory();


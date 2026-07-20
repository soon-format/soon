import { encodeAll, type FormatResult } from "./formats";
import { SAMPLES } from "./samples";
import "./style.css";

const BRAND = {
  soon: "#4F46E5",
  toon: "#D97706",
  gcf: "#059669",
  json: "#6B7280",
};

function pctSaving(json: number, fmt: number): string {
  if (json === 0) return "—";
  const pct = ((1 - fmt / json) * 100).toFixed(1);
  return `${Number(pct) >= 0 ? "+" : ""}${pct}%`;
}

function savingClass(json: number, fmt: number): string {
  if (json === 0) return "";
  return fmt < json ? "saving-positive" : fmt > json ? "saving-negative" : "";
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function renderPanel(
  result: FormatResult,
  jsonChars: number,
  color: string,
): string {
  if (result.error) {
    return `
      <div class="panel">
        <div class="panel-header" style="border-color: ${color}">
          <span class="panel-name">${result.name}</span>
          <span class="panel-error">Error</span>
        </div>
        <pre class="panel-output error-output">${escapeHtml(result.error)}</pre>
      </div>`;
  }

  const saving = pctSaving(jsonChars, result.chars);
  const cls = savingClass(jsonChars, result.chars);

  return `
    <div class="panel">
      <div class="panel-header" style="border-color: ${color}">
        <span class="panel-name">${result.name}</span>
        <span class="panel-stats">
          <span class="char-count">${result.chars.toLocaleString()} chars</span>
          <span class="saving ${cls}">${saving}</span>
        </span>
      </div>
      <pre class="panel-output">${escapeHtml(result.output)}</pre>
    </div>`;
}

function run() {
  const inputEl = document.getElementById("json-input") as HTMLTextAreaElement;
  const raw = inputEl.value.trim();
  if (!raw) return;

  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch (e) {
    const errDiv = document.getElementById("parse-error")!;
    errDiv.textContent = `Invalid JSON: ${e instanceof Error ? e.message : e}`;
    errDiv.style.display = "block";
    document.getElementById("results")!.innerHTML = "";
    return;
  }
  document.getElementById("parse-error")!.style.display = "none";

  const results = encodeAll(data);
  const jsonChars = results.json.chars;

  const html = `
    <div class="summary-bar">
      <div class="summary-item">
        <span class="summary-label">JSON baseline</span>
        <span class="summary-value">${jsonChars.toLocaleString()} chars</span>
      </div>
      <div class="summary-item" style="--accent: ${BRAND.soon}">
        <span class="summary-label">SOON</span>
        <span class="summary-value ${savingClass(jsonChars, results.soon.chars)}">${results.soon.error ? "error" : pctSaving(jsonChars, results.soon.chars)}</span>
      </div>
      <div class="summary-item" style="--accent: ${BRAND.toon}">
        <span class="summary-label">TOON</span>
        <span class="summary-value ${savingClass(jsonChars, results.toon.chars)}">${results.toon.error ? "error" : pctSaving(jsonChars, results.toon.chars)}</span>
      </div>
      <div class="summary-item" style="--accent: ${BRAND.gcf}">
        <span class="summary-label">GCF</span>
        <span class="summary-value ${savingClass(jsonChars, results.gcf.chars)}">${results.gcf.error ? "error" : pctSaving(jsonChars, results.gcf.chars)}</span>
      </div>
    </div>
    <div class="panels">
      ${renderPanel(results.soon, jsonChars, BRAND.soon)}
      ${renderPanel(results.toon, jsonChars, BRAND.toon)}
      ${renderPanel(results.gcf, jsonChars, BRAND.gcf)}
    </div>`;

  document.getElementById("results")!.innerHTML = html;
}

function loadSample(index: number) {
  const sample = SAMPLES[index];
  const inputEl = document.getElementById("json-input") as HTMLTextAreaElement;
  inputEl.value = JSON.stringify(sample.data, null, 2);
  run();
}

function mount() {
  const app = document.getElementById("app")!;

  const sampleButtons = SAMPLES.map(
    (s, i) =>
      `<button class="sample-btn" data-index="${i}" title="${s.description}">${s.name}</button>`,
  ).join("");

  app.innerHTML = `
    <header>
      <h1>SOON Playground</h1>
      <p class="subtitle">Paste JSON and compare <strong>SOON</strong>, <strong>TOON</strong>, and <strong>GCF</strong> encodings side by side.</p>
    </header>
    <div class="input-section">
      <div class="input-toolbar">
        <label for="json-input">Input JSON</label>
        <div class="sample-buttons">${sampleButtons}</div>
      </div>
      <textarea id="json-input" spellcheck="false" placeholder='{"users": [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Linus"}]}'></textarea>
      <div id="parse-error" class="parse-error" style="display:none"></div>
    </div>
    <div id="results"></div>`;

  const inputEl = document.getElementById("json-input") as HTMLTextAreaElement;

  let debounceTimer: ReturnType<typeof setTimeout>;
  inputEl.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(run, 300);
  });

  app.querySelectorAll<HTMLButtonElement>(".sample-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      loadSample(Number(btn.dataset.index));
    });
  });

  loadSample(1);
}

mount();

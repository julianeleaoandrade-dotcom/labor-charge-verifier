// Browser front end for labor-charge-verifier.
// Loads Python (Pyodide) in the page, then runs the same Python package as the
// command-line tool. Selected files are read in the browser and written to
// Pyodide's in-memory file system; nothing is sent over the network.

const PYODIDE_VERSION = "0.27.7";
const DEFAULT_INDEX_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

// Python modules copied next to this page by the GitHub Pages workflow.
// tests/test_web.py checks this list against src/labor_charge_verifier/.
const PACKAGE_MODULES = [
  "__init__", "cli", "common", "invoice_check", "price_adjustment", "report", "rules",
  "wage_check",
];

const MODULES = {
  invoice: {
    runner: "run_invoice",
    files: [
      ["contract.csv", "Contract: posts, headcount and unit prices"],
      ["roster.csv", "Employee list for the contract"],
      ["timesheets.csv", "Timesheets: hours by employee, post and day"],
      ["payroll.csv", "Payroll: hours and pay by employee and week"],
      ["invoice.csv", "Invoice lines and the stated total"],
    ],
  },
  wages: {
    runner: "run_wages",
    files: [
      ["contract.csv", "Contract (for the wage determination number)"],
      ["roster.csv", "Employee list with occupations"],
      ["payroll.csv", "Payroll: hours and pay by employee and week"],
      ["wage_determination.csv", "Wage determination rates (copy from sam.gov)",
        "wage_determination_SAMPLE.csv"],
    ],
  },
  price: {
    runner: "run_price",
    files: [
      ["price_adjustment_input.csv", "Rates before and after the new wage determination"],
    ],
  },
};

const state = { pyodide: null, module: "invoice", files: { invoice: {}, wages: {}, price: {} } };
const $ = (selector) => document.querySelector(selector);

function setStatus(text, kind) {
  const el = $("#status");
  el.textContent = text;
  el.className = `status ${kind}`;
  el.hidden = !text;
}

function indexURL() {
  // A same-origin path can be given for offline testing: ?pyodide=/pyodide/
  const local = new URLSearchParams(location.search).get("pyodide");
  if (local && local.startsWith("/") && !local.startsWith("//")) return local;
  return DEFAULT_INDEX_URL;
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.onload = resolve;
    script.onerror = () => reject(new Error(`Could not load ${src}`));
    document.head.appendChild(script);
  });
}

async function fetchText(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Could not load ${path} (${response.status})`);
  return response.text();
}

async function fetchBytes(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Could not load ${path} (${response.status})`);
  return new Uint8Array(await response.arrayBuffer());
}

async function startPython() {
  const base = indexURL();
  await loadScript(`${base}pyodide.js`);
  const pyodide = await globalThis.loadPyodide({ indexURL: base });
  await pyodide.loadPackage(["pandas", "pyyaml"]);
  const fs = pyodide.FS;
  fs.mkdirTree("/lcv/labor_charge_verifier");
  fs.mkdirTree("/lcv/config");
  for (const name of PACKAGE_MODULES) {
    fs.writeFile(`/lcv/labor_charge_verifier/${name}.py`,
      await fetchText(`py/labor_charge_verifier/${name}.py`));
  }
  fs.writeFile("/lcv/config/settings.example.yaml", await fetchText("config/settings.example.yaml"));
  fs.writeFile("/lcv/runner.py", await fetchText("runner.py"));
  pyodide.runPython("import sys; sys.path.insert(0, '/lcv'); import runner");
  return pyodide;
}

function call(name, ...args) {
  const runner = state.pyodide.pyimport("runner");
  const result = JSON.parse(runner[name](...args));
  runner.destroy();
  return result;
}

function buildFileRows() {
  for (const container of document.querySelectorAll(".files")) {
    const module = container.dataset.module;
    const config = MODULES[module];
    const list = document.createElement("ul");
    list.className = "file-list";
    for (const [name, label] of config.files) {
      const item = document.createElement("li");
      const id = `file-${module}-${name.replace(/\W/g, "-")}`;
      item.innerHTML = `
        <label for="${id}"><span class="file-label">${label}</span>
          <code>${name}</code></label>
        <input type="file" id="${id}" accept=".csv,text/csv">
        <span class="file-state" data-state-for="${name}">Not added</span>
        <a href="templates/${name}" download>Blank template</a>`;
      item.querySelector("input").addEventListener("change", async (event) => {
        const file = event.target.files[0];
        if (!file) return;
        state.files[module][name] = { bytes: new Uint8Array(await file.arrayBuffer()),
          label: file.name };
        refresh();
      });
      list.appendChild(item);
    }
    const sample = document.createElement("button");
    sample.type = "button";
    sample.className = "secondary";
    sample.textContent = "Use sample data";
    sample.addEventListener("click", () => useSample(module));
    container.append(list, sample);
  }
}

async function useSample(module) {
  try {
    for (const [name, , sampleName] of MODULES[module].files) {
      state.files[module][name] = {
        bytes: await fetchBytes(`sample-data/${sampleName || name}`),
        label: "sample data (fictitious)",
      };
    }
    if (module === "price" && !$("#as-of").value) $("#as-of").value = today();
    refresh();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

function today() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function missingFiles() {
  return MODULES[state.module].files.map(([name]) => name)
    .filter((name) => !state.files[state.module][name]);
}

function refresh() {
  for (const container of document.querySelectorAll(".files")) {
    const module = container.dataset.module;
    for (const el of container.querySelectorAll("[data-state-for]")) {
      const entry = state.files[module][el.dataset.stateFor];
      el.textContent = entry ? `Added: ${entry.label}` : "Not added";
      el.classList.toggle("added", Boolean(entry));
    }
  }
  const missing = missingFiles();
  const ready = Boolean(state.pyodide) && missing.length === 0;
  $("#run").disabled = !ready;
  $("#run-help").textContent = !state.pyodide ? "Waiting for the checking engine to load."
    : missing.length ? `Still needed: ${missing.join(", ")}.` : "Ready.";
}

function selectTab(module) {
  state.module = module;
  for (const tab of document.querySelectorAll("[role=tab]")) {
    const selected = tab.id === `tab-${module}`;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
  }
  for (const panel of document.querySelectorAll("[role=tabpanel]")) {
    panel.hidden = panel.id !== `panel-${module}`;
  }
  $("#results").hidden = true;
  refresh();
}

function overrides() {
  const values = {};
  for (const name of ["hw_rate", "hours_tolerance", "suta", "workers_compensation"]) {
    values[name] = $(`#set-${name}`).value;
  }
  return JSON.stringify(values);
}

function count(n, word) {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

function money(value) {
  return Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function showResult(result) {
  const summary = $("#summary");
  if (!result.ok) {
    summary.innerHTML = `<p class="error-box"><strong>The files could not be checked.</strong> ${escapeHtml(result.error)}</p>`;
    $("#downloads").innerHTML = "";
    $("#report").hidden = true;
    $("#results").hidden = false;
    return;
  }
  const s = result.summary;
  if (state.module === "price") {
    summary.innerHTML = `
      <p class="big">Total adjustment: <strong>USD ${money(s.total_adjustment)}</strong></p>
      <p>Notice deadline: ${s.deadlines.map(escapeHtml).join("; ") || "no date given"}</p>
      ${s.warnings.length ? `<ul class="warnings">${s.warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join("")}</ul>` : ""}`;
  } else {
    const billing = state.module === "invoice" ? `
      <div class="card over"><span>Overbilled</span><strong>USD ${money(s.overbilled_amount)}</strong><small>${count(s.overbilled_count, "finding")}</small></div>
      <div class="card under"><span>Underbilled</span><strong>USD ${money(s.underbilled_amount)}</strong><small>${count(s.underbilled_count, "finding")}</small></div>` : "";
    summary.innerHTML = `
      <p>${count(s.findings, "finding")} (${s.high} high, ${s.medium} medium, ${s.low} low).</p>
      <div class="cards">${billing}
        <div class="card owed"><span>Owed to workers</span><strong>USD ${money(s.owed_to_workers)}</strong><small>${count(s.underpaid_worker_count, "finding")}</small></div>
      </div>`;
  }
  const downloads = $("#downloads");
  downloads.innerHTML = "<span>Download:</span>";
  for (const [name, content] of Object.entries(result.downloads)) {
    const type = name.endsWith(".csv") ? "text/csv" : name.endsWith(".html") ? "text/html" : "text/markdown";
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([content], { type: `${type};charset=utf-8` }));
    link.download = name;
    link.textContent = name;
    downloads.appendChild(link);
  }
  const frame = $("#report");
  frame.hidden = false;
  frame.srcdoc = result.report_html;
  $("#results").hidden = false;
  $("#results").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function run() {
  const module = state.module;
  const button = $("#run");
  button.disabled = true;
  setStatus("Checking...", "loading");
  try {
    const fs = state.pyodide.FS;
    const dir = `/work/${module}`;
    state.pyodide.runPython(`import shutil, os; shutil.rmtree("${dir}", ignore_errors=True); os.makedirs("${dir}")`);
    for (const [name, entry] of Object.entries(state.files[module])) {
      fs.writeFile(`${dir}/${name}`, entry.bytes);
    }
    const config = MODULES[module];
    const result = module === "price"
      ? call(config.runner, `${dir}/price_adjustment_input.csv`, overrides(), $("#as-of").value)
      : call(config.runner, dir, overrides());
    showResult(result);
    setStatus("", "ok");
  } catch (error) {
    showResult({ ok: false, error: error.message });
    setStatus("", "ok");
  } finally {
    refresh();
  }
}

async function main() {
  buildFileRows();
  for (const tab of document.querySelectorAll("[role=tab]")) {
    tab.addEventListener("click", () => selectTab(tab.id.replace("tab-", "")));
  }
  $("#run").addEventListener("click", run);
  selectTab("invoice");
  try {
    state.pyodide = await startPython();
    const defaults = call("defaults");
    for (const name of ["hw_rate", "hours_tolerance", "suta", "workers_compensation"]) {
      $(`#set-${name}`).value = defaults[name];
    }
    $("#version").textContent = `version ${defaults.version}`;
    setStatus("", "ok");
  } catch (error) {
    setStatus(`The checking engine could not load (${error.message}). Check your internet `
      + "connection and reload the page. The command-line version works offline.", "error");
  }
  refresh();
}

main();

const state = {
  selectedKey: "fixtures",
  status: null,
};

const readyBadge = document.querySelector("#readyBadge");
const reliabilityBanner = document.querySelector("#reliabilityBanner");
const fileList = document.querySelector("#fileList");
const preview = document.querySelector("#preview");
const message = document.querySelector("#message");
const refreshBtn = document.querySelector("#refreshBtn");
const loadExamplesBtn = document.querySelector("#loadExamplesBtn");
const runBtn = document.querySelector("#runBtn");
const useElo = document.querySelector("#useElo");
const useFifa = document.querySelector("#useFifa");
const useOdds = document.querySelector("#useOdds");
const marketWeight = document.querySelector("#marketWeight");
const marketWeightValue = document.querySelector("#marketWeightValue");

function showMessage(text, isError = false) {
  message.hidden = false;
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function clearMessage() {
  message.hidden = true;
  message.textContent = "";
  message.classList.remove("error");
}

function fileBadge(file) {
  if (file.error) return ["error", "Erreur"];
  if (!file.exists) return [file.required ? "missing" : "warn", file.required ? "Manquant" : "Optionnel"];
  if (file.missing_columns.length) return ["warn", "Colonnes"];
  return ["ok", "OK"];
}

function renderFiles() {
  const files = [...state.status.files, ...state.status.outputs];
  fileList.innerHTML = "";
  for (const file of files) {
    const [badgeClass, badgeText] = fileBadge(file);
    const card = document.createElement("button");
    card.type = "button";
    card.className = `file-card ${state.selectedKey === file.key ? "active" : ""}`;
    card.innerHTML = `
      <div class="file-title">
        <span>${file.label}</span>
        <span class="badge ${badgeClass}">${badgeText}</span>
      </div>
      <div class="file-meta">${file.path}</div>
      <div class="file-meta">${file.rows} lignes · ${file.columns.length} colonnes</div>
    `;
    card.addEventListener("click", () => {
      state.selectedKey = file.key;
      render();
    });
    fileList.appendChild(card);
  }
}

function renderPreview() {
  const files = [...state.status.files, ...state.status.outputs];
  const file = files.find((item) => item.key === state.selectedKey) || files[0];
  if (!file) {
    preview.innerHTML = '<div class="preview-empty">Aucun fichier suivi.</div>';
    return;
  }
  if (file.error) {
    preview.innerHTML = `<div class="preview-empty">${file.error}</div>`;
    return;
  }
  if (!file.exists) {
    preview.innerHTML = `<div class="preview-empty">Fichier absent: ${file.path}</div>`;
    return;
  }
  if (file.missing_columns.length) {
    preview.innerHTML = `<div class="preview-empty">Colonnes manquantes: ${file.missing_columns.join(", ")}</div>`;
    return;
  }
  if (!file.preview.length) {
    preview.innerHTML = '<div class="preview-empty">Fichier présent mais vide.</div>';
    return;
  }

  const columns = Object.keys(file.preview[0]);
  const header = columns.map((column) => `<th>${column}</th>`).join("");
  const rows = file.preview
    .map((row) => `<tr>${columns.map((column) => `<td>${row[column]}</td>`).join("")}</tr>`)
    .join("");
  preview.innerHTML = `<table><thead><tr>${header}</tr></thead><tbody>${rows}</tbody></table>`;
}

function renderReliability() {
  const reliability = state.status.reliability;
  if (!reliability) {
    reliabilityBanner.hidden = true;
    return;
  }
  reliabilityBanner.hidden = false;
  reliabilityBanner.textContent = reliability.message;
  reliabilityBanner.classList.toggle("ok", reliability.ok);
  reliabilityBanner.classList.toggle("danger", !reliability.ok);
}

function render() {
  readyBadge.textContent = state.status.ready ? "Prêt" : "Données requises";
  readyBadge.className = `status-pill ${state.status.ready ? "ready" : "missing"}`;
  renderReliability();
  renderFiles();
  renderPreview();
}

async function refreshStatus() {
  const response = await fetch("/api/status");
  state.status = await response.json();
  if (!state.status.files.some((file) => file.key === state.selectedKey)) {
    state.selectedKey = "fixtures";
  }
  render();
}

async function postJson(url, payload = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Erreur inconnue");
  }
  return data;
}

async function withBusy(button, label, task) {
  const original = button.textContent;
  button.disabled = true;
  button.textContent = label;
  try {
    await task();
  } finally {
    button.disabled = false;
    button.textContent = original;
  }
}

refreshBtn.addEventListener("click", () => {
  withBusy(refreshBtn, "Actualisation", async () => {
    clearMessage();
    await refreshStatus();
  });
});

loadExamplesBtn.addEventListener("click", () => {
  withBusy(loadExamplesBtn, "Copie", async () => {
    clearMessage();
    const result = await postJson("/api/load-examples");
    state.status = result.status;
    showMessage(`Exemples copiés: ${result.copied.join(", ")}`);
    render();
  }).catch((error) => showMessage(error.message, true));
});

runBtn.addEventListener("click", () => {
  withBusy(runBtn, "Calcul", async () => {
    clearMessage();
    const result = await postJson("/api/run", {
      use_elo: useElo.checked,
      use_fifa: useFifa.checked,
      use_odds: useOdds.checked,
      market_weight: Number(marketWeight.value),
    });
    state.status = result.status;
    state.selectedKey = "predictions";
    showMessage(`${result.rows} prédictions écrites dans ${result.csv} et ${result.markdown}`);
    render();
  }).catch((error) => showMessage(error.message, true));
});

marketWeight.addEventListener("input", () => {
  marketWeightValue.textContent = Number(marketWeight.value).toFixed(2);
});

refreshStatus().catch((error) => showMessage(error.message, true));

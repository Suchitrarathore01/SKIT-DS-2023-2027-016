/**
 * ChainShield Chrome Extension – popup.js
 *
 * Vanilla JS — no bundler, no framework.
 * Runs in the popup context (NOT a content script or service worker).
 *
 * Architecture notes:
 * - The extension calls the FastAPI backend directly via fetch().
 * - The backend URL is set by BACKEND_URL below. Change this for production.
 * - No blockchain calls are made from the extension — that is the backend's job.
 * - No tabs or activeTab permissions are used; the user pastes the URL manually.
 */

"use strict";

// ─── Configuration ────────────────────────────────────────────────────────────

/**
 * Backend base URL.
 * For local development this must match the host_permissions entry in manifest.json.
 * For production, update both this constant AND the manifest's host_permissions.
 */
const BACKEND_URL = "http://127.0.0.1:8000";

/**
 * (Optional) Dashboard URL shown in the footer link.
 * Set to an empty string to hide the link.
 */
const DASHBOARD_URL = "http://localhost:5173";

// ─── DOM references ───────────────────────────────────────────────────────────
const form           = document.getElementById("scan-form");
const urlInput       = document.getElementById("url-input");
const scanBtn        = document.getElementById("scan-btn");
const validationMsg  = document.getElementById("validation-msg");
const dashboardLink  = document.getElementById("dashboard-link");

const stateIdle      = document.getElementById("state-idle");
const stateLoading   = document.getElementById("state-loading");
const stateError     = document.getElementById("state-error");
const stateResult    = document.getElementById("state-result");

const errorMsg       = document.getElementById("error-msg");
const errorHint      = document.getElementById("error-hint");

const resultBadge    = document.getElementById("result-badge");
const resultDomain   = document.getElementById("result-domain");

const detailHttpsVal = document.getElementById("detail-https-val");
const detailIpVal    = document.getElementById("detail-ip-val");

const blockchainSec  = document.getElementById("blockchain-section");
const blockchainMsg  = document.getElementById("blockchain-msg");

const findingsSec    = document.getElementById("findings-section");
const findingsList   = document.getElementById("findings-list");
const noFindings     = document.getElementById("no-findings");

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Show one state panel, hide others. */
function showState(name) {
  const states = [
    { name: "idle", el: stateIdle },
    { name: "loading", el: stateLoading },
    { name: "error", el: stateError },
    { name: "result", el: stateResult },
  ];

  for (const s of states) {
    if (s.el) {
      if (s.name === name) {
        s.el.hidden = false;
        s.el.removeAttribute("hidden");
        s.el.style.display = "";
      } else {
        s.el.hidden = true;
        s.el.setAttribute("hidden", "");
        s.el.style.display = "none";
      }
    }
  }
}

/** Returns true if value looks like a valid http(s) URL. */
function isValidUrl(value) {
  try {
    const u = new URL(value.trim());
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

/** Build the risk badge class name from the backend risk_level string. */
function badgeClass(level) {
  const map = { SAFE: "badge-safe", MEDIUM: "badge-medium", HIGH: "badge-high" };
  return map[(level || "").toUpperCase()] ?? "badge-unknown";
}

/** Build the badge label from the risk_level string. */
function badgeLabel(level) {
  const l = (level || "UNKNOWN").toUpperCase();
  const icons = { SAFE: "✓", MEDIUM: "!", HIGH: "✕", UNKNOWN: "?" };
  const labels = { SAFE: "Safe", MEDIUM: "Medium Risk", HIGH: "High Risk", UNKNOWN: "Unknown" };
  return `${icons[l] ?? "?"} ${labels[l] ?? "Unknown"}`;
}

// ─── API call ─────────────────────────────────────────────────────────────────

async function callScanApi(url) {
  let response;

  try {
    response = await fetch(`${BACKEND_URL}/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
  } catch (networkErr) {
    throw {
      type: "network",
      message: "Cannot reach the ChainShield backend.",
      hint: `Make sure the server is running at ${BACKEND_URL}`,
    };
  }

  if (!response.ok) {
    let detail = "";
    try {
      const body = await response.json();
      detail = body.detail || body.message || "";
    } catch { /* ignore */ }
    throw {
      type: "http",
      message: `Server error ${response.status}: ${detail || response.statusText}`,
    };
  }

  try {
    return await response.json();
  } catch {
    throw { type: "parse", message: "Unexpected response format from server." };
  }
}

// ─── Render result ────────────────────────────────────────────────────────────

function renderResult(data) {
  const {
    domain,
    https,
    uses_ip,
    risk_level,
    findings = [],
    blockchain_available,
    blockchain_found,
  } = data;

  // ── Risk badge ──
  resultBadge.className = `badge ${badgeClass(risk_level)}`;
  resultBadge.textContent = badgeLabel(risk_level);
  resultBadge.setAttribute("aria-label", `Risk level: ${risk_level || "UNKNOWN"}`);

  // ── Domain ──
  resultDomain.textContent = domain || "";

  // ── HTTPS pill ──
  detailHttpsVal.textContent = https ? "Yes" : "No";
  detailHttpsVal.className   = `pill ${https ? "pill-yes" : "pill-no"}`;

  // ── IP pill ──
  detailIpVal.textContent = uses_ip ? "Yes" : "No";
  detailIpVal.className   = `pill ${uses_ip ? "pill-no" : "pill-yes"}`;

  // ── Blockchain status ──
  if (typeof blockchain_available === "boolean") {
    blockchainSec.hidden = false;
    if (!blockchain_available) {
      blockchainSec.className = "blockchain-section blockchain-unavailable";
      blockchainMsg.textContent =
        "Registry unavailable during this scan. This does not indicate safety.";
    } else if (blockchain_found) {
      blockchainSec.className = "blockchain-section blockchain-found";
      blockchainMsg.textContent =
        "⚠ URL found in blockchain threat registry.";
    } else {
      blockchainSec.className = "blockchain-section blockchain-clear";
      blockchainMsg.textContent =
        "Registry checked — URL hash not found. Absence does not guarantee safety.";
    }
  } else {
    blockchainSec.hidden = true;
  }

  // ── Findings ──
  if (findings.length > 0) {
    findingsSec.hidden = false;
    noFindings.hidden  = true;
    // Clear previous findings
    findingsList.innerHTML = "";
    for (const f of findings) {
      const li = document.createElement("li");
      // findings are plain text strings from the backend — safe to set as text
      li.textContent = f;
      findingsList.appendChild(li);
    }
  } else {
    findingsSec.hidden = true;
    noFindings.hidden  = false;
  }

  showState("result");
}

// ─── Form submit ──────────────────────────────────────────────────────────────

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = urlInput.value.trim();

  // Client-side validation
  validationMsg.hidden = true;
  urlInput.classList.remove("input-error");

  if (!url) {
    validationMsg.textContent = "Please enter a URL.";
    validationMsg.hidden = false;
    urlInput.classList.add("input-error");
    return;
  }
  if (!isValidUrl(url)) {
    validationMsg.textContent = "Enter a URL starting with http:// or https://";
    validationMsg.hidden = false;
    urlInput.classList.add("input-error");
    return;
  }

  // Show loading
  scanBtn.disabled = true;
  scanBtn.textContent = "Scanning…";
  urlInput.disabled = true;
  showState("loading");

  try {
    const data = await callScanApi(url);
    renderResult(data);
  } catch (err) {
    errorMsg.textContent = err.message || "An unexpected error occurred.";
    if (err.hint) {
      errorHint.textContent = err.hint;
      errorHint.hidden = false;
    } else {
      errorHint.hidden = true;
    }
    showState("error");
  } finally {
    scanBtn.disabled = false;
    scanBtn.textContent = "Scan";
    urlInput.disabled = false;
    if (stateLoading) {
      stateLoading.hidden = true;
      stateLoading.setAttribute("hidden", "");
      stateLoading.style.display = "none";
    }
  }
});

// ─── Initialise ───────────────────────────────────────────────────────────────

// Show dashboard link if configured
if (DASHBOARD_URL) {
  dashboardLink.href = DASHBOARD_URL;
  dashboardLink.hidden = false;
}

// Reset scan button and start in idle state
scanBtn.disabled = false;
scanBtn.textContent = "Scan";
urlInput.disabled = false;
showState("idle");

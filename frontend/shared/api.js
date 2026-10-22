/**
 * ChainShield – Shared API Client
 *
 * Single source of truth for all backend communication.
 * Import this module from both the dashboard and the extension.
 *
 * Dashboard:  reads VITE_API_BASE_URL from the Vite environment.
 * Extension:  passes the base URL explicitly via the `baseUrl` parameter
 *             or falls back to DEFAULT_BASE_URL.
 */

// ─── Default base URL ────────────────────────────────────────────────────────
// In ES modules / browser contexts, default to the local FastAPI server.
export const DEFAULT_BASE_URL = "http://127.0.0.1:8000";

// ─── Core fetch wrapper ───────────────────────────────────────────────────────
/**
 * Generic fetch helper. Throws a structured error object on any failure so
 * callers can distinguish network errors from HTTP errors from bad JSON.
 *
 * @param {string} path      - e.g. "/scan"
 * @param {object} options   - standard fetch options
 * @param {string} [baseUrl] - override for caller (dashboard or extension)
 * @returns {Promise<any>}   - parsed JSON body
 */
export async function apiFetch(path, options = {}, baseUrl = DEFAULT_BASE_URL) {
  // Normalize base URL without trailing slash
  const cleanBase = (baseUrl || DEFAULT_BASE_URL).replace(/\/+$/, "");
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${cleanBase}${cleanPath}`;

  let response;
  try {
    response = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (networkError) {
    throw {
      type: "network",
      message: "Cannot reach the ChainShield backend. Is the server running?",
      detail: networkError?.message || String(networkError),
    };
  }

  if (!response.ok) {
    let detail = "";
    try {
      const body = await response.json();
      detail = body.detail || body.message || JSON.stringify(body);
    } catch {
      detail = await response.text().catch(() => "");
    }
    throw {
      type: "http",
      status: response.status,
      message: `Server returned ${response.status}: ${detail || response.statusText}`,
      detail,
    };
  }

  try {
    return await response.json();
  } catch {
    throw {
      type: "parse",
      message: "The server returned a response that could not be parsed.",
    };
  }
}

// ─── Public API methods ───────────────────────────────────────────────────────

/**
 * POST /scan
 * Scan a URL for phishing / smishing threats.
 *
 * @param {string} url      - The URL to scan (must be a valid URL string)
 * @param {string} [baseUrl] - API host URL
 * @returns {Promise<ScanResponse>}
 *
 * ScanResponse shape (from backend schema):
 * {
 *   url: string,
 *   status: string,          // "processed" | "error"
 *   message: string,
 *   protocol: string,
 *   domain: string,
 *   path: string,
 *   https: boolean,
 *   uses_ip: boolean,
 *   risk_level: string,      // "SAFE" | "MEDIUM" | "HIGH" | "UNKNOWN"
 *   findings: string[],
 *   blockchain_available: boolean,
 *   blockchain_found: boolean,
 * }
 */
export async function scanUrl(url, baseUrl = DEFAULT_BASE_URL) {
  return apiFetch(
    "/scan",
    { method: "POST", body: JSON.stringify({ url }) },
    baseUrl
  );
}

/**
 * GET /scan/history
 * Retrieve all previously scanned URLs from the database.
 *
 * NOTE: History records do NOT include blockchain_available / blockchain_found
 * because those fields are not persisted to the database. Do not attempt to
 * display them from history entries.
 *
 * History item shape:
 * {
 *   id: number,
 *   url: string,
 *   status: string,
 *   message: string,
 *   protocol: string,
 *   domain: string,
 *   path: string,
 *   https: boolean,
 *   uses_ip: boolean,
 *   risk_level: string,
 *   findings: string[],
 * }
 *
 * @param {string} [baseUrl] - API host URL
 * @returns {Promise<Array<HistoryItem>>}
 */
export async function getScanHistory(baseUrl = DEFAULT_BASE_URL) {
  return apiFetch("/scan/history", { method: "GET" }, baseUrl);
}

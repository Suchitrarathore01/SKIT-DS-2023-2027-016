import { useState } from "react";
import { scanUrl } from "../api.js";
import ScanResult from "./ScanResult.jsx";
import "./UrlScanner.css";

// ─── Simple client-side URL validation ───────────────────────────────────────
// This is for usability only — the backend is authoritative.
function isValidUrl(value) {
  try {
    const u = new URL(value.trim());
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

// ─── Skeleton loader for scan in progress ────────────────────────────────────
function ScanSkeleton() {
  return (
    <div className="scan-skeleton card" aria-busy="true" aria-label="Loading scan result">
      <div className="skeleton" style={{ width: "65%", height: "18px", marginBottom: "12px" }} />
      <div className="skeleton" style={{ width: "40%", height: "12px", marginBottom: "24px" }} />
      <div className="skeleton" style={{ width: "100%", height: "80px", marginBottom: "12px" }} />
      <div className="skeleton" style={{ width: "80%", height: "12px" }} />
    </div>
  );
}

// ─── UrlScanner ──────────────────────────────────────────────────────────────
/**
 * UrlScanner
 *
 * Self-contained URL input + scan form.  Calls POST /scan and renders
 * the result via <ScanResult>.  All state (loading, result, error) is local.
 *
 * Props:
 *   initialUrl {string}  – optional pre-filled URL (e.g. from Overview CTA)
 */
export default function UrlScanner({ initialUrl = "" }) {
  const [url, setUrl] = useState(initialUrl);
  const [validationError, setValidationError] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [apiError, setApiError] = useState(null);

  function handleChange(e) {
    setUrl(e.target.value);
    // Clear validation error as the user types
    if (validationError) setValidationError("");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const trimmed = url.trim();

    // Client-side validation (usability gate — backend validates authoritatively)
    if (!trimmed) {
      setValidationError("Please enter a URL to scan.");
      return;
    }
    if (!isValidUrl(trimmed)) {
      setValidationError(
        "Enter a full URL starting with http:// or https://"
      );
      return;
    }

    setValidationError("");
    setResult(null);
    setApiError(null);
    setLoading(true);

    try {
      const data = await scanUrl(trimmed);
      setResult(data);
    } catch (err) {
      setApiError(err);
    } finally {
      setLoading(false);
    }
  }

  function handleClear() {
    setUrl("");
    setResult(null);
    setApiError(null);
    setValidationError("");
  }

  return (
    <div className="url-scanner">
      {/* ── Scan form ── */}
      <form onSubmit={handleSubmit} noValidate className="scanner-form">
        <div className="scanner-input-row">
          <label htmlFor="url-input" className="sr-only">
            URL to scan
          </label>
          <input
            id="url-input"
            type="url"
            className={`input scanner-input${validationError ? " input-error" : ""}`}
            placeholder="https://example.com/path?query=value"
            value={url}
            onChange={handleChange}
            disabled={loading}
            autoComplete="url"
            spellCheck="false"
            aria-describedby={validationError ? "url-error" : undefined}
            aria-invalid={!!validationError}
          />
          <button
            type="submit"
            className="btn btn-primary btn-lg"
            disabled={loading}
          >
            {loading ? "Scanning…" : "Scan URL"}
          </button>
        </div>

        {validationError && (
          <p id="url-error" className="scanner-validation-error" role="alert">
            {validationError}
          </p>
        )}
      </form>

      {/* ── Loading skeleton ── */}
      {loading && <ScanSkeleton />}

      {/* ── API error ── */}
      {!loading && apiError && (
        <div className="error-box scanner-error" role="alert">
          <strong>Scan failed:</strong> {apiError.message}
          {apiError.type === "network" && (
            <p className="scanner-error-hint">
              Make sure the backend is running at{" "}
              <code>
                {import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"}
              </code>
            </p>
          )}
        </div>
      )}

      {/* ── Scan result ── */}
      {!loading && result && (
        <>
          <ScanResult result={result} />
          <button
            className="btn btn-secondary scanner-clear-btn"
            onClick={handleClear}
            type="button"
          >
            Scan another URL
          </button>
        </>
      )}
    </div>
  );
}

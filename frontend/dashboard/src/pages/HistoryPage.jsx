import { useEffect, useState, useCallback } from "react";
import { getScanHistory } from "../api.js";
import RiskBadge from "../components/RiskBadge.jsx";
import ScanResult from "../components/ScanResult.jsx";
import "./HistoryPage.css";

// ─── Skeleton row ─────────────────────────────────────────────────────────────
function HistorySkeleton() {
  return (
    <div className="history-skeleton" aria-busy="true" aria-label="Loading history">
      {[1, 2, 3].map((n) => (
        <div key={n} className="history-skeleton-row card">
          <div className="skeleton" style={{ width: "55%", height: "14px" }} />
          <div className="skeleton" style={{ width: "20%", height: "14px" }} />
          <div className="skeleton" style={{ width: "30%", height: "14px" }} />
        </div>
      ))}
    </div>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────
function EmptyHistory() {
  return (
    <div className="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 8v4l3 3" strokeLinecap="round" />
      </svg>
      <p>No scans yet.</p>
      <p className="empty-hint">
        Use the{" "}
        <a href="/scanner">URL Scanner</a>
        {" "}to analyse your first URL.
      </p>
    </div>
  );
}

// ─── History row ──────────────────────────────────────────────────────────────
/**
 * A single collapsible row in the history table.
 * Clicking it expands/collapses the full ScanResult detail panel.
 *
 * NOTE: history records from GET /scan/history do NOT include
 * blockchain_available or blockchain_found — those fields are not persisted.
 * ScanResult handles this gracefully (no blockchain section shown when absent).
 */
function HistoryRow({ item }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <li className="history-item">
      <button
        className="history-row"
        onClick={() => setExpanded((e) => !e)}
        aria-expanded={expanded}
        aria-controls={`history-detail-${item.id}`}
      >
        <span className="history-col history-col-id">#{item.id}</span>
        <span className="history-col history-col-url" title={item.url}>
          {item.url}
        </span>
        <span className="history-col history-col-domain">{item.domain || "—"}</span>
        <span className="history-col history-col-badge">
          <RiskBadge level={item.risk_level} />
        </span>
        <span
          className={`history-chevron${expanded ? " history-chevron-open" : ""}`}
          aria-hidden="true"
        >
          ▾
        </span>
      </button>

      {expanded && (
        <div
          id={`history-detail-${item.id}`}
          className="history-detail"
        >
          <ScanResult result={item} />
        </div>
      )}
    </li>
  );
}

// ─── HistoryPage ──────────────────────────────────────────────────────────────
export default function HistoryPage() {
  const [history, setHistory] = useState(null); // null = loading
  const [error, setError] = useState(null);

  const loadHistory = useCallback(async () => {
    setError(null);
    setHistory(null); // reset to loading state on refresh
    try {
      const data = await getScanHistory();
      // Validate that we received an array — guard against unexpected response shapes
      if (!Array.isArray(data)) {
        throw {
          type: "parse",
          message: "Unexpected response from /scan/history — expected an array.",
        };
      }
      // Show most recent first (the DB returns insertion order; highest id = newest)
      setHistory([...data].reverse());
    } catch (err) {
      setError(err);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  return (
    <div className="history-page">
      {/* ── Header ── */}
      <div className="history-header">
        <div>
          <h1 className="section-title" style={{ marginBottom: 0 }}>
            Scan History
          </h1>
          <p className="section-subtitle" style={{ margin: 0 }}>
            All URLs previously scanned during this session. Click a row to
            expand details.
          </p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={loadHistory}
          disabled={history === null}
          aria-label="Refresh scan history"
        >
          ↻ Refresh
        </button>
      </div>

      {/* ── Note about blockchain fields ── */}
      <p className="history-note">
        <strong>Note:</strong> Blockchain registry status is not stored in the
        database and is not shown in history. Run a fresh scan to see blockchain
        results for a URL.
      </p>

      {/* ── Loading ── */}
      {history === null && !error && <HistorySkeleton />}

      {/* ── Error ── */}
      {error && (
        <div className="error-box" role="alert">
          <strong>Could not load history:</strong> {error.message}
          <br />
          <button
            className="btn btn-secondary"
            style={{ marginTop: "var(--space-3)" }}
            onClick={loadHistory}
          >
            Try again
          </button>
        </div>
      )}

      {/* ── Empty state ── */}
      {history !== null && history.length === 0 && <EmptyHistory />}

      {/* ── History list ── */}
      {history !== null && history.length > 0 && (
        <div className="history-table-wrapper">
          {/* Column headers */}
          <div className="history-table-header" aria-hidden="true">
            <span className="history-col history-col-id">#</span>
            <span className="history-col history-col-url">URL</span>
            <span className="history-col history-col-domain">Domain</span>
            <span className="history-col history-col-badge">Risk</span>
            <span style={{ width: "24px" }} />
          </div>
          <ul className="history-list" aria-label="Scan history">
            {history.map((item) => (
              <HistoryRow key={item.id} item={item} />
            ))}
          </ul>
          <p className="history-count">
            {history.length} scan{history.length !== 1 ? "s" : ""} on record
          </p>
        </div>
      )}
    </div>
  );
}

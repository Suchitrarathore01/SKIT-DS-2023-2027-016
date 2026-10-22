import RiskBadge from "./RiskBadge.jsx";
import "./ScanResult.css";

/**
 * ScanResult
 *
 * Renders the full details of a completed scan.
 * Accepts either a "live" scan response (from POST /scan — includes blockchain
 * fields) or a history record (from GET /scan/history — blockchain fields absent).
 *
 * Props:
 *   result {object} – the scan object from the API
 */
export default function ScanResult({ result }) {
  if (!result) return null;

  const {
    url,
    status,
    message,
    domain,
    protocol,
    path,
    https,
    uses_ip,
    risk_level,
    findings = [],
    // These are only present on live scan responses, not history records:
    blockchain_available,
    blockchain_found,
  } = result;

  const hasBlockchainData =
    typeof blockchain_available === "boolean";

  return (
    <div className="scan-result card">
      {/* ── Header ── */}
      <div className="sr-header">
        <div className="sr-header-left">
          <h2 className="sr-url" title={url}>
            {url}
          </h2>
          {status === "error" && (
            <p className="sr-error-note">{message}</p>
          )}
        </div>
        <div className="sr-header-right">
          <RiskBadge level={risk_level} />
        </div>
      </div>

      <div className="divider" />

      {/* ── URL breakdown ── */}
      <section className="sr-section" aria-label="URL details">
        <h3 className="sr-section-title">URL Details</h3>
        <dl className="sr-grid">
          <div className="sr-field">
            <dt>Domain</dt>
            <dd className="mono">{domain || "—"}</dd>
          </div>
          <div className="sr-field">
            <dt>Protocol</dt>
            <dd className="mono">{protocol || "—"}</dd>
          </div>
          <div className="sr-field">
            <dt>Path</dt>
            <dd className="mono">{path || "/"}</dd>
          </div>
          <div className="sr-field">
            <dt>HTTPS</dt>
            <dd>
              {https ? (
                <span className="pill pill-green">Yes</span>
              ) : (
                <span className="pill pill-red">No</span>
              )}
            </dd>
          </div>
          <div className="sr-field">
            <dt>Uses IP address</dt>
            <dd>
              {uses_ip ? (
                <span className="pill pill-red">Yes</span>
              ) : (
                <span className="pill pill-green">No</span>
              )}
            </dd>
          </div>
        </dl>
      </section>

      <div className="divider" />

      {/* ── Security findings ── */}
      <section className="sr-section" aria-label="Security findings">
        <h3 className="sr-section-title">
          Security Findings
          {findings.length > 0 && (
            <span className="finding-count">{findings.length}</span>
          )}
        </h3>
        {findings.length === 0 ? (
          <p className="sr-no-findings">
            No security issues detected by the heuristic scanner.
          </p>
        ) : (
          <ul className="finding-list">
            {findings.map((finding, i) => (
              // findings are plain text strings from the backend — safe to render
              <li key={i} className="finding-item">
                <span className="finding-icon" aria-hidden="true">⚠</span>
                <span>{finding}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* ── Blockchain status (only available on live scan results) ── */}
      {hasBlockchainData && (
        <>
          <div className="divider" />
          <section className="sr-section" aria-label="Blockchain registry status">
            <h3 className="sr-section-title">Blockchain Registry</h3>
            {!blockchain_available ? (
              <p className="sr-blockchain-note sr-bc-unavailable">
                The blockchain registry was not reachable during this scan.
                This does not indicate the URL is safe.
              </p>
            ) : blockchain_found ? (
              <p className="sr-blockchain-note sr-bc-threat">
                This URL's hash was found in the blockchain threat registry.
              </p>
            ) : (
              <p className="sr-blockchain-note sr-bc-clear">
                Registry checked — this URL's hash was not found. Note: absence
                from the registry does not guarantee the URL is safe.
              </p>
            )}
          </section>
        </>
      )}

      {/* ── Disclaimer ── */}
      <div className="divider" />
      <p className="sr-disclaimer">
        ChainShield uses heuristic checks and a blockchain threat registry.
        A "Safe" result does not guarantee the URL is free from all threats.
        Exercise caution before visiting unknown links.
      </p>
    </div>
  );
}

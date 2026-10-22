import { Link } from "react-router-dom";
import "./OverviewPage.css";

/**
 * OverviewPage
 *
 * Static overview of the ChainShield system.
 *
 * Design decision: the backend history endpoint returns individual scan records
 * but does not expose aggregate statistics (total threats, accuracy, etc.).
 * Rather than fabricate numbers, this page explains how ChainShield works and
 * directs users to the Scanner and History pages.
 */
export default function OverviewPage() {
  return (
    <div className="overview-page">
      {/* ── Hero ── */}
      <section className="overview-hero card">
        <div className="hero-icon" aria-hidden="true">
          <svg viewBox="0 0 64 72" fill="none">
            <path
              d="M32 4L8 15v20c0 15.5 11 30 24 34 13-4 24-18.5 24-34V15L32 4z"
              fill="#0e7490"
              stroke="#0c6680"
              strokeWidth="2"
            />
            <path
              d="M22 36l7 7 13-13"
              stroke="#fff"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <div className="hero-text">
          <h1 className="hero-title">ChainShield</h1>
          <p className="hero-subtitle">
            Blockchain-backed phishing and smishing detection
          </p>
          <p className="hero-description">
            ChainShield scans URLs for phishing and smishing indicators using
            heuristic security checks and a decentralised blockchain threat
            registry deployed on the Ethereum Sepolia testnet. Known threat
            hashes are looked up instantly; findings from heuristic checks are
            surfaced alongside the registry result.
          </p>
          <div className="hero-actions">
            <Link to="/scanner" className="btn btn-primary btn-lg">
              Scan a URL
            </Link>
            <Link to="/history" className="btn btn-secondary btn-lg">
              View History
            </Link>
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="overview-how">
        <h2 className="section-title">How It Works</h2>
        <div className="how-cards">
          {HOW_STEPS.map((step) => (
            <div key={step.number} className="how-card card">
              <span className="how-step-number" aria-hidden="true">
                {step.number}
              </span>
              <h3 className="how-step-title">{step.title}</h3>
              <p className="how-step-desc">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Detection methods ── */}
      <section className="overview-methods">
        <h2 className="section-title">Detection Methods</h2>
        <div className="method-list card">
          {METHODS.map((m) => (
            <div key={m.label} className="method-item">
              <span className="method-icon" aria-hidden="true">
                {m.icon}
              </span>
              <div>
                <p className="method-label">{m.label}</p>
                <p className="method-desc">{m.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Disclaimer ── */}
      <p className="overview-disclaimer">
        ChainShield is a final-year research project. Scan results are
        informational only and do not constitute a guarantee of safety.
        Always exercise judgement before visiting unknown links.
      </p>
    </div>
  );
}

// ─── Static data ──────────────────────────────────────────────────────────────
const HOW_STEPS = [
  {
    number: "1",
    title: "Submit URL",
    desc: "Enter any URL in the scanner. The backend validates it and begins analysis immediately.",
  },
  {
    number: "2",
    title: "Heuristic Checks",
    desc: "The backend checks for HTTPS, IP-based domains, suspicious characters, and phishing keywords.",
  },
  {
    number: "3",
    title: "Blockchain Lookup",
    desc: "The URL hash is checked against the on-chain ThreatRegistry contract on Ethereum Sepolia. If found, a finding is added.",
  },
  {
    number: "4",
    title: "Risk Assessment",
    desc: "A risk level (Safe · Medium · High) is calculated from the total number of findings and returned with full details.",
  },
];

const METHODS = [
  {
    icon: "🔒",
    label: "HTTPS Verification",
    desc: "Flags URLs not using encrypted HTTPS connections.",
  },
  {
    icon: "🌐",
    label: "IP Address Detection",
    desc: "Identifies URLs using raw IP addresses instead of domain names — a common phishing tactic.",
  },
  {
    icon: "🔍",
    label: "Suspicious Character & Keyword Analysis",
    desc: "Scans for characters like @, %, \\ and keywords such as 'login', 'verify', 'password'.",
  },
  {
    icon: "⛓",
    label: "Blockchain Registry",
    desc: "Compares the URL hash against a decentralised registry of confirmed threats on Ethereum Sepolia. Registry unavailability does not imply safety.",
  },
];

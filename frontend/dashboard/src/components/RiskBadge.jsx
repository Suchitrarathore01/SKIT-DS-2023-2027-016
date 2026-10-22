/**
 * RiskBadge
 *
 * Displays a colour-coded pill for the scan risk level returned by the backend.
 * Valid values: "SAFE" | "MEDIUM" | "HIGH" | "UNKNOWN"
 *
 * The badge maps directly to CSS classes defined in index.css.
 */

const RISK_MAP = {
  SAFE:    { label: "Safe",    cls: "badge-safe",    icon: "✓" },
  MEDIUM:  { label: "Medium",  cls: "badge-medium",  icon: "!" },
  HIGH:    { label: "High",    cls: "badge-high",    icon: "✕" },
  UNKNOWN: { label: "Unknown", cls: "badge-unknown", icon: "?" },
};

/**
 * @param {{ level: string }} props
 */
export default function RiskBadge({ level }) {
  const key = (level || "UNKNOWN").toUpperCase();
  const { label, cls, icon } = RISK_MAP[key] ?? RISK_MAP.UNKNOWN;

  return (
    <span className={`badge ${cls}`} aria-label={`Risk level: ${label}`}>
      <span aria-hidden="true">{icon}</span>
      {label}
    </span>
  );
}

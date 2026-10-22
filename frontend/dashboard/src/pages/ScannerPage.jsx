import UrlScanner from "../components/UrlScanner.jsx";
import "./ScannerPage.css";

/**
 * ScannerPage
 *
 * Wraps the UrlScanner component with a page header.
 */
export default function ScannerPage() {
  return (
    <div className="scanner-page">
      <div className="scanner-page-header">
        <h1 className="section-title" style={{ marginBottom: 0 }}>
          URL Scanner
        </h1>
        <p className="section-subtitle" style={{ margin: 0 }}>
          Enter a URL to check it against heuristic security rules and the
          blockchain threat registry.
        </p>
      </div>
      <UrlScanner />
    </div>
  );
}

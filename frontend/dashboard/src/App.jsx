import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import OverviewPage from "./pages/OverviewPage.jsx";
import ScannerPage from "./pages/ScannerPage.jsx";
import HistoryPage from "./pages/HistoryPage.jsx";

/**
 * App – top-level route table.
 * All pages share the Layout (sidebar + topbar).
 */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        {/* Default route → overview */}
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="scanner" element={<ScannerPage />} />
        <Route path="history" element={<HistoryPage />} />
        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Route>
    </Routes>
  );
}

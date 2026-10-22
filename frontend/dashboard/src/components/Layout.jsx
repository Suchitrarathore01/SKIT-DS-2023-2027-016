import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import "./Layout.css";

// ─── Navigation items ─────────────────────────────────────────────────────────
const NAV_ITEMS = [
  {
    to: "/overview",
    label: "Overview",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
  },
  {
    to: "/scanner",
    label: "URL Scanner",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="11" cy="11" r="8" />
        <path d="m21 21-4.35-4.35" />
      </svg>
    ),
  },
  {
    to: "/history",
    label: "Scan History",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M12 8v4l3 3" />
        <circle cx="12" cy="12" r="9" />
      </svg>
    ),
  },
];

// ─── Logo mark ────────────────────────────────────────────────────────────────
function ShieldLogo() {
  return (
    <svg className="logo-icon" viewBox="0 0 40 44" fill="none" aria-hidden="true">
      <path
        d="M20 2L4 9v12c0 9.5 6.8 18.4 16 21 9.2-2.6 16-11.5 16-21V9L20 2z"
        fill="#0e7490"
        stroke="#0c6680"
        strokeWidth="1.5"
      />
      <path
        d="M14 21l4 4 8-8"
        stroke="#fff"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// ─── Layout component ─────────────────────────────────────────────────────────
export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const closeSidebar = () => setSidebarOpen(false);

  return (
    <div className="layout">
      {/* ── Mobile overlay ── */}
      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}

      {/* ── Sidebar ── */}
      <aside className={`sidebar${sidebarOpen ? " sidebar-open" : ""}`}>
        <div className="sidebar-header">
          <ShieldLogo />
          <div className="sidebar-brand">
            <span className="brand-name">ChainShield</span>
            <span className="brand-tagline">Threat Detection</span>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="Main navigation">
          <ul>
            {NAV_ITEMS.map(({ to, label, icon }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  className={({ isActive }) =>
                    `nav-link${isActive ? " nav-link-active" : ""}`
                  }
                  onClick={closeSidebar}
                >
                  <span className="nav-icon">{icon}</span>
                  <span>{label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className="sidebar-footer">
          <span className="sidebar-version">v0.1.0 · Final Year Project</span>
        </div>
      </aside>

      {/* ── Main area ── */}
      <div className="layout-main">
        {/* Top bar */}
        <header className="topbar">
          <button
            className="menu-toggle hide-desktop"
            onClick={() => setSidebarOpen((o) => !o)}
            aria-label="Toggle navigation menu"
            aria-expanded={sidebarOpen}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" width="22" height="22">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <div className="topbar-title hide-mobile">
            <ShieldLogo />
            <span>ChainShield</span>
          </div>
          <div className="topbar-right">
            <span className="topbar-badge">
              <span className="status-dot" aria-hidden="true" />
              Blockchain Registry
            </span>
          </div>
        </header>

        {/* Page content */}
        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

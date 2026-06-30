import { useState } from "react";
import { Routes, Route, NavLink } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import Dashboard from "./pages/Dashboard";
import Transactions from "./pages/Transactions";
import Recurring from "./pages/Recurring";
import Transfers from "./pages/Transfers";
import Salaries from "./pages/Salaries";
import Upload from "./pages/Upload";
import Settings from "./pages/Settings";
import EmailImports from "./pages/EmailImports";
import Templates from "./pages/Templates";
import Login from "./pages/Login";
import AuthCallback from "./pages/AuthCallback";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/transactions", label: "Transactions" },
  { to: "/recurring", label: "Recurring" },
  { to: "/transfers", label: "Transfers" },
  { to: "/salaries", label: "Salaries" },
  { to: "/upload", label: "Upload" },
  { to: "/templates", label: "Templates" },
  { to: "/email-imports", label: "Email Imports" },
  { to: "/settings", label: "Settings" },
];

const DEMO_EMAIL = "demo@montrack.app";

function AuthedApp() {
  const { token, email, logout } = useAuth();
  const isDemo = email === DEMO_EMAIL;
  const [menuOpen, setMenuOpen] = useState(false);

  if (!token) {
    return (
      <Routes>
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="*" element={<Login />} />
      </Routes>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <nav className="sticky top-0 z-10 bg-slate-900/95 backdrop-blur-sm border-b border-slate-800 px-4 sm:px-6 py-3">
        <div className="flex items-center gap-1">
          <span className="font-bold text-sm mr-6 bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
            Money Tracker
          </span>
          <div className="hidden md:flex items-center gap-1">
            {navItems.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  isActive
                    ? "text-indigo-400 font-medium text-sm px-3 py-1.5 rounded-md bg-indigo-500/10"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800 text-sm px-3 py-1.5 rounded-md transition-colors"
                }
              >
                {label}
              </NavLink>
            ))}
          </div>
          <div className="ml-auto hidden md:flex items-center gap-3">
            {isDemo && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30 font-medium">
                Demo · read-only
              </span>
            )}
            <span className="text-slate-500 text-xs">{email}</span>
            <button
              onClick={logout}
              className="text-slate-400 hover:text-slate-200 text-sm px-3 py-1.5 rounded-md hover:bg-slate-800 transition-colors"
            >
              Sign out
            </button>
          </div>
          <button
            onClick={() => setMenuOpen((open) => !open)}
            aria-label="Toggle menu"
            aria-expanded={menuOpen}
            className="ml-auto md:hidden text-slate-400 hover:text-slate-200 p-2 rounded-md hover:bg-slate-800 transition-colors"
          >
            {menuOpen ? (
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            ) : (
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            )}
          </button>
        </div>

        {menuOpen && (
          <div className="md:hidden mt-3 flex flex-col gap-1 pb-1">
            {navItems.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                onClick={() => setMenuOpen(false)}
                className={({ isActive }) =>
                  isActive
                    ? "text-indigo-400 font-medium text-sm px-3 py-2 rounded-md bg-indigo-500/10"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800 text-sm px-3 py-2 rounded-md transition-colors"
                }
              >
                {label}
              </NavLink>
            ))}
            <div className="border-t border-slate-800 mt-2 pt-2 flex items-center justify-between px-3">
              <div className="flex items-center gap-2">
                {isDemo && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30 font-medium">
                    Demo · read-only
                  </span>
                )}
                <span className="text-slate-500 text-xs">{email}</span>
              </div>
              <button
                onClick={logout}
                className="text-slate-400 hover:text-slate-200 text-sm px-3 py-1.5 rounded-md hover:bg-slate-800 transition-colors"
              >
                Sign out
              </button>
            </div>
          </div>
        )}
      </nav>

      <main className="px-4 sm:px-6 py-6 max-w-7xl mx-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/recurring" element={<Recurring />} />
          <Route path="/transfers" element={<Transfers />} />
          <Route path="/salaries" element={<Salaries />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/templates" element={<Templates />} />
          <Route path="/email-imports" element={<EmailImports />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/auth/callback" element={<AuthCallback />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AuthedApp />
    </AuthProvider>
  );
}

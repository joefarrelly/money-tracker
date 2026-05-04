import { Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Transactions from "./pages/Transactions";
import Recurring from "./pages/Recurring";
import Transfers from "./pages/Transfers";
import Salaries from "./pages/Salaries";
import Upload from "./pages/Upload";
import Settings from "./pages/Settings";
import EmailImports from "./pages/EmailImports";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/transactions", label: "Transactions" },
  { to: "/recurring", label: "Recurring" },
  { to: "/transfers", label: "Transfers" },
  { to: "/salaries", label: "Salaries" },
  { to: "/upload", label: "Upload" },
  { to: "/email-imports", label: "Email Imports" },
  { to: "/settings", label: "Settings" },
];

export default function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <nav className="sticky top-0 z-10 bg-slate-900/95 backdrop-blur-sm border-b border-slate-800 px-6 py-3 flex items-center gap-1">
        <span className="font-bold text-sm mr-6 bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
          Money Tracker
        </span>
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
      </nav>

      <main className="px-6 py-6 max-w-7xl mx-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/recurring" element={<Recurring />} />
          <Route path="/transfers" element={<Transfers />} />
          <Route path="/salaries" element={<Salaries />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/email-imports" element={<EmailImports />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}

import { Routes, Route, NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  CreditCard,
  ArrowDownUp,
  Target,
  Upload,
  DollarSign,
  MessageSquare,
  TrendingUp,
  Repeat,
  Heart,
  Zap,
  FileText,
  RefreshCw,
} from "lucide-react";
import Dashboard from "./pages/Dashboard";
import Debts from "./pages/Debts";
import Transactions from "./pages/Transactions";
import Budgets from "./pages/Budgets";
import Import from "./pages/Import";
import Accounts from "./pages/Accounts";
import NLPEntry from "./pages/NLPEntry";
import Forecast from "./pages/Forecast";
import Subscriptions from "./pages/Subscriptions";
import HealthScore from "./pages/HealthScore";
import Scenarios from "./pages/Scenarios";
import Reports from "./pages/Reports";
import Automation from "./pages/Automation";

const navSections = [
  {
    label: "Core",
    items: [
      { to: "/", icon: LayoutDashboard, label: "Dashboard" },
      { to: "/accounts", icon: DollarSign, label: "Accounts" },
      { to: "/transactions", icon: ArrowDownUp, label: "Transactions" },
      { to: "/debts", icon: CreditCard, label: "Debts" },
      { to: "/budgets", icon: Target, label: "Budgets" },
      { to: "/import", icon: Upload, label: "Import" },
    ],
  },
  {
    label: "AI Tools",
    items: [
      { to: "/nlp", icon: MessageSquare, label: "Quick Entry" },
      { to: "/forecast", icon: TrendingUp, label: "Forecast" },
      { to: "/subscriptions", icon: Repeat, label: "Subscriptions" },
      { to: "/health", icon: Heart, label: "Health Score" },
      { to: "/scenarios", icon: Zap, label: "Scenarios" },
      { to: "/reports", icon: FileText, label: "Reports" },
      { to: "/automation", icon: RefreshCw, label: "Automation" },
    ],
  },
];

export default function App() {
  return (
    <div className="flex min-h-screen bg-gray-900">
      {/* Sidebar */}
      <nav className="w-56 bg-gray-800 border-r border-gray-700 p-4 flex flex-col gap-1 overflow-y-auto">
        <h1 className="text-xl font-bold text-emerald-400 mb-4 px-3">
          DebtFree
        </h1>
        {navSections.map((section) => (
          <div key={section.label} className="mb-3">
            <p className="text-xs text-gray-500 uppercase tracking-wider px-3 mb-1">
              {section.label}
            </p>
            {section.items.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                    isActive
                      ? "bg-emerald-600 text-white"
                      : "text-gray-400 hover:text-white hover:bg-gray-700"
                  }`
                }
              >
                <Icon size={16} />
                {label}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      {/* Main content */}
      <main className="flex-1 p-6 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/debts" element={<Debts />} />
          <Route path="/budgets" element={<Budgets />} />
          <Route path="/import" element={<Import />} />
          <Route path="/nlp" element={<NLPEntry />} />
          <Route path="/forecast" element={<Forecast />} />
          <Route path="/subscriptions" element={<Subscriptions />} />
          <Route path="/health" element={<HealthScore />} />
          <Route path="/scenarios" element={<Scenarios />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/automation" element={<Automation />} />
        </Routes>
      </main>
    </div>
  );
}

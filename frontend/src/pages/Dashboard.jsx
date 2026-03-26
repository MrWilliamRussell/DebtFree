import { useEffect, useState } from "react";
import {
  PieChart, Pie, Cell,
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Legend,
} from "recharts";
import { getDashboardSummary } from "../api";

const COLORS = [
  "#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6",
  "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#84cc16",
];

function StatCard({ label, value, color = "text-white" }) {
  return (
    <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
      <p className="text-gray-400 text-sm">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getDashboardSummary()
      .then((r) => setData(r.data))
      .catch(() => setError("Backend not reachable. Start with docker compose up."));
  }, []);

  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-red-400 text-lg">{error}</p>
        <p className="text-gray-500 mt-2">Run: <code className="bg-gray-800 px-2 py-1 rounded">docker compose up --build</code></p>
      </div>
    );
  }

  if (!data) {
    return <p className="text-gray-400 py-10">Loading dashboard...</p>;
  }

  const categoryData = Object.entries(data.expenses_by_category).map(
    ([name, value]) => ({ name, value: Math.round(value * 100) / 100 })
  );

  const essentialData = [
    { name: "Essential", value: data.essential_vs_discretionary.essential },
    { name: "Discretionary", value: data.essential_vs_discretionary.discretionary },
  ];

  const fmt = (n) => `$${Number(n).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Financial Dashboard</h2>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Monthly Income" value={fmt(data.total_income_monthly)} color="text-emerald-400" />
        <StatCard label="Monthly Expenses" value={fmt(data.total_expenses_monthly)} color="text-red-400" />
        <StatCard
          label="Net Monthly"
          value={fmt(data.net_monthly)}
          color={data.net_monthly >= 0 ? "text-emerald-400" : "text-red-400"}
        />
        <StatCard label="Total Debt" value={fmt(data.total_debt)} color="text-orange-400" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Min. Payments" value={fmt(data.total_minimum_payments)} />
        <StatCard
          label="Debt-to-Income"
          value={`${data.debt_to_income_ratio}%`}
          color={data.debt_to_income_ratio > 36 ? "text-red-400" : "text-emerald-400"}
        />
      </div>

      {/* Charts */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Expenses by Category */}
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4">Expenses by Category</h3>
          {categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={categoryData} dataKey="value" nameKey="name" outerRadius={100} label>
                  {categoryData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => fmt(v)} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-500 py-10 text-center">No expenses this month</p>
          )}
        </div>

        {/* Essential vs Discretionary */}
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4">Essential vs Discretionary</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={essentialData}>
              <XAxis dataKey="name" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip formatter={(v) => fmt(v)} />
              <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                <Cell fill="#10b981" />
                <Cell fill="#f59e0b" />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Suggested cuts */}
      {data.top_cuts.length > 0 && (
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <h3 className="text-lg font-semibold mb-3">Suggested Cuts</h3>
          <ul className="space-y-2">
            {data.top_cuts.map((cut, i) => (
              <li key={i} className="flex justify-between items-center bg-gray-700 rounded-lg px-4 py-2">
                <span className="capitalize">{cut.category}</span>
                <span className="text-red-400 font-semibold">{fmt(cut.amount)}/mo</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

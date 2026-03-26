import { useEffect, useState } from "react";
import {
  AreaChart, Area, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, Cell,
  ReferenceLine, CartesianGrid,
} from "recharts";

const API_BASE = "/api";

export default function Overview() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/overview/`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => setError("Backend not reachable. Run: docker compose up --build"));
  }, []);

  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-red-400 text-lg">{error}</p>
      </div>
    );
  }
  if (!data) return <p className="text-gray-400 py-10">Loading overview...</p>;

  const fmt = (n) => `$${Number(n).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;
  const fmtK = (n) => n >= 1000 ? `$${(n / 1000).toFixed(1)}k` : fmt(n);

  const onBudget = data.debt_free_scenarios?.on_budget || {};
  const minOnly = data.debt_free_scenarios?.minimum_only || {};
  const aggressive = data.debt_free_scenarios?.aggressive || {};

  const trendColor = data.spending_trend === "falling" ? "text-emerald-400"
    : data.spending_trend === "rising" ? "text-red-400" : "text-gray-400";
  const trendArrow = data.spending_trend === "falling" ? "↓"
    : data.spending_trend === "rising" ? "↑" : "→";

  const severityColors = {
    high: "border-red-600 bg-red-900/20",
    medium: "border-yellow-600 bg-yellow-900/20",
    low: "border-blue-600 bg-blue-900/20",
    good: "border-emerald-600 bg-emerald-900/20",
  };
  const severityTextColors = {
    high: "text-red-400",
    medium: "text-yellow-400",
    low: "text-blue-400",
    good: "text-emerald-400",
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">System Overview</h2>

      {/* ── Alerts Banner ── */}
      {data.alerts.length > 0 && (
        <div className="space-y-2">
          {data.alerts.map((alert, i) => (
            <div key={i} className={`rounded-xl p-4 border ${severityColors[alert.severity]}`}>
              <div className="flex justify-between items-start">
                <div>
                  <p className={`font-bold ${severityTextColors[alert.severity]}`}>{alert.title}</p>
                  <p className="text-sm text-gray-300 mt-1">{alert.message}</p>
                </div>
                {alert.months_impact && (
                  <div className="text-right ml-4">
                    <p className="text-2xl font-bold text-red-400">+{alert.months_impact}</p>
                    <p className="text-xs text-gray-400">months added</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Debt-Free Date Cards ── */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <p className="text-gray-400 text-xs uppercase tracking-wide">If You Stick to Budget</p>
          <p className="text-3xl font-bold text-emerald-400 mt-2">
            {onBudget.debt_free_date || "—"}
          </p>
          <p className="text-sm text-gray-400 mt-1">
            {onBudget.months} months · {fmt(onBudget.monthly_payment || 0)}/mo
          </p>
          <p className="text-xs text-gray-500">Interest: {fmt(onBudget.total_interest || 0)}</p>
        </div>
        <div className="bg-gray-800 rounded-xl p-5 border border-yellow-700/50">
          <p className="text-gray-400 text-xs uppercase tracking-wide">Minimum Payments Only</p>
          <p className="text-3xl font-bold text-yellow-400 mt-2">
            {minOnly.debt_free_date || "—"}
          </p>
          <p className="text-sm text-gray-400 mt-1">
            {minOnly.months} months · {fmt(minOnly.monthly_payment || 0)}/mo
          </p>
          <p className="text-xs text-gray-500">Interest: {fmt(minOnly.total_interest || 0)}</p>
        </div>
        <div className="bg-gray-800 rounded-xl p-5 border border-blue-700/50">
          <p className="text-gray-400 text-xs uppercase tracking-wide">Aggressive (Cut 15% More)</p>
          <p className="text-3xl font-bold text-blue-400 mt-2">
            {aggressive.debt_free_date || "—"}
          </p>
          <p className="text-sm text-gray-400 mt-1">
            {aggressive.months} months · {fmt(aggressive.monthly_payment || 0)}/mo
          </p>
          <p className="text-xs text-gray-500">Interest: {fmt(aggressive.total_interest || 0)}</p>
        </div>
      </div>

      {/* ── Key Metrics Row ── */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Stat label="Total Debt" value={fmt(data.total_debt)} color="text-red-400" />
        <Stat label="Monthly Income" value={fmt(data.monthly_income)} color="text-emerald-400" />
        <Stat label="Avg Expenses" value={fmt(data.avg_monthly_expenses)} color="text-orange-400" />
        <Stat
          label="Spending Trend"
          value={`${trendArrow} ${Math.abs(data.spending_trend_pct)}%`}
          color={trendColor}
        />
        <Stat
          label="Budget Adherence"
          value={`${data.budget_adherence_pct}%`}
          color={data.budget_adherence_pct >= 80 ? "text-emerald-400" : "text-red-400"}
        />
      </div>

      {/* ── Debt Burndown Chart ── */}
      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
        <h3 className="text-lg font-semibold mb-1">Debt Burndown</h3>
        <p className="text-xs text-gray-500 mb-4">
          Projected month-by-month remaining balance based on current payment plan.
          The line should trend to $0 — that's your debt-free date.
        </p>
        {data.burndown.length > 0 ? (
          <ResponsiveContainer width="100%" height={350}>
            <AreaChart data={data.burndown}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="month"
                stroke="#9ca3af"
                tick={{ fontSize: 11 }}
                interval={Math.max(Math.floor(data.burndown.length / 12), 0)}
              />
              <YAxis stroke="#9ca3af" tickFormatter={fmtK} />
              <Tooltip
                formatter={(v, name) => [fmt(v), name === "balance" ? "Remaining Debt" : name]}
                contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "8px" }}
              />
              <ReferenceLine y={0} stroke="#10b981" strokeDasharray="3 3" label={{ value: "DEBT FREE", fill: "#10b981", fontSize: 11 }} />
              <defs>
                <linearGradient id="burndownGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.1} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="balance"
                stroke="#ef4444"
                strokeWidth={2}
                fill="url(#burndownGradient)"
                name="Remaining Debt"
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-gray-500 text-center py-10">Add debts to see your burndown chart.</p>
        )}
      </div>

      {/* ── Spending History Chart ── */}
      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
        <h3 className="text-lg font-semibold mb-1">Monthly Spending Trend</h3>
        <p className="text-xs text-gray-500 mb-4">
          12-month spending history — essential vs discretionary. Downward trend = faster debt payoff.
        </p>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data.spending_history}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="month" stroke="#9ca3af" tick={{ fontSize: 10 }} />
            <YAxis stroke="#9ca3af" tickFormatter={fmtK} />
            <Tooltip
              formatter={(v) => fmt(v)}
              contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "8px" }}
            />
            <Legend />
            <Bar dataKey="essential" name="Essential" stackId="a" fill="#3b82f6" radius={[0, 0, 0, 0]} />
            <Bar dataKey="discretionary" name="Discretionary" stackId="a" fill="#f59e0b" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* ── Budget Status + Debt Breakdown side by side ── */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Budget Status */}
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <h3 className="text-lg font-semibold mb-3">Budget Status</h3>
          {data.budget_status.length > 0 ? (
            <div className="space-y-3">
              {data.budget_status.map((b, i) => (
                <div key={i}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="capitalize">{b.category.replace("_", " ")}</span>
                    <span className={b.over ? "text-red-400 font-bold" : "text-gray-400"}>
                      {fmt(b.spent)} / {fmt(b.limit)} ({b.pct}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2.5">
                    <div
                      className={`h-2.5 rounded-full transition-all ${
                        b.pct >= 100 ? "bg-red-500" : b.pct >= 80 ? "bg-yellow-500" : "bg-emerald-500"
                      }`}
                      style={{ width: `${Math.min(b.pct, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-sm py-4">No budgets set. Go to Budgets to add spending limits.</p>
          )}
        </div>

        {/* Debt Breakdown */}
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <h3 className="text-lg font-semibold mb-3">Debt Breakdown</h3>
          {data.debts.length > 0 ? (
            <div className="space-y-3">
              {data.debts.map((d, i) => {
                const pctOfTotal = data.total_debt > 0 ? (d.balance / data.total_debt * 100) : 0;
                return (
                  <div key={i}>
                    <div className="flex justify-between text-sm mb-1">
                      <span>{d.name}</span>
                      <span className="text-red-400 font-semibold">{fmt(d.balance)}</span>
                    </div>
                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                      <span>{d.rate}% APR · {fmt(d.min_payment)}/mo min</span>
                      <span>{pctOfTotal.toFixed(0)}% of total</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                      <div
                        className="h-2 rounded-full bg-red-500"
                        style={{ width: `${pctOfTotal}%` }}
                      />
                    </div>
                  </div>
                );
              })}
              <div className="border-t border-gray-600 pt-2 mt-2 flex justify-between font-bold">
                <span>Total</span>
                <span className="text-red-400">{fmt(data.total_debt)}</span>
              </div>
            </div>
          ) : (
            <p className="text-gray-500 text-sm py-4">No debts added yet. Go to Debts to add your balances.</p>
          )}
        </div>
      </div>

      {/* ── What the Numbers Mean ── */}
      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
        <h3 className="font-semibold mb-3">How to Read This</h3>
        <div className="grid md:grid-cols-2 gap-4 text-sm text-gray-400">
          <div>
            <p className="text-white font-semibold mb-1">Burndown Chart</p>
            <p>Shows your total debt decreasing over time. The line should slope down to $0.
            If it flattens or rises, you're not paying enough to beat the interest.</p>
          </div>
          <div>
            <p className="text-white font-semibold mb-1">Debt-Free Date</p>
            <p>Three scenarios: on-budget (your plan), minimum only (worst case),
            and aggressive (cut 15% more spending). The gap between them is your opportunity.</p>
          </div>
          <div>
            <p className="text-white font-semibold mb-1">Spending Trend</p>
            <p>The stacked bar chart shows 12 months of spending. Blue = essentials you can't easily cut.
            Yellow = discretionary — every dollar you cut here accelerates debt payoff.</p>
          </div>
          <div>
            <p className="text-white font-semibold mb-1">Alerts</p>
            <p>Red alerts mean your spending is pushing out your debt-free date.
            The system recalculates in real-time: overspend $200 → see exactly how many extra months it costs you.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, color = "text-white" }) {
  return (
    <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
      <p className="text-gray-400 text-xs uppercase tracking-wide">{label}</p>
      <p className={`text-xl font-bold mt-1 ${color}`}>{value}</p>
    </div>
  );
}

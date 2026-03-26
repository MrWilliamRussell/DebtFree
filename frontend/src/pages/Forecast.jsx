import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
  AreaChart, Area,
} from "recharts";
import { getForecast } from "../api";

const COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"];

export default function Forecast() {
  const [data, setData] = useState(null);
  const [months, setMonths] = useState(6);
  const [loading, setLoading] = useState(false);

  const runForecast = async () => {
    setLoading(true);
    try {
      const r = await getForecast({ months_ahead: months });
      setData(r.data);
    } catch {
      setData(null);
    }
    setLoading(false);
  };

  const fmt = (n) => `$${Number(n).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

  const trendIcon = { rising: "trending up", falling: "trending down", stable: "stable" };
  const trendColor = { rising: "text-red-400", falling: "text-emerald-400", stable: "text-gray-400" };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Spending Forecast</h2>
      <p className="text-gray-400">AI-powered prediction of future spending patterns and debt-free timeline.</p>

      <div className="flex gap-4 items-end">
        <div>
          <label className="text-sm text-gray-400 block mb-1">Months ahead</label>
          <input
            type="number" min={1} max={24} value={months}
            onChange={(e) => setMonths(parseInt(e.target.value))}
            className="bg-gray-700 rounded-lg px-3 py-2 text-sm w-24"
          />
        </div>
        <button
          onClick={runForecast} disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg px-6 py-2 text-sm font-semibold transition-colors"
        >
          {loading ? "Forecasting..." : "Run Forecast"}
        </button>
      </div>

      {data && (
        <>
          {/* Debt-Free Projection */}
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            <h3 className="text-lg font-semibold mb-4">Debt-Free Timeline</h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-gray-700 rounded-lg p-4">
                <p className="text-gray-400 text-xs">Current Path</p>
                <p className="text-2xl font-bold text-orange-400">{data.debt_free_projection.current_months} mo</p>
                <p className="text-xs text-gray-500">Interest: {fmt(data.debt_free_projection.current_interest)}</p>
              </div>
              <div className="bg-gray-700 rounded-lg p-4">
                <p className="text-gray-400 text-xs">Cut 15%</p>
                <p className="text-2xl font-bold text-emerald-400">{data.debt_free_projection.optimistic_months} mo</p>
                <p className="text-xs text-gray-500">Interest: {fmt(data.debt_free_projection.optimistic_interest)}</p>
              </div>
              <div className="bg-gray-700 rounded-lg p-4">
                <p className="text-gray-400 text-xs">Forecasted Trend</p>
                <p className="text-2xl font-bold text-blue-400">{data.debt_free_projection.forecasted_months} mo</p>
                <p className="text-xs text-gray-500">Interest: {fmt(data.debt_free_projection.forecasted_interest)}</p>
              </div>
            </div>
          </div>

          {/* Alert Categories */}
          {data.alert_categories.length > 0 && (
            <div className="bg-red-900/20 border border-red-700 rounded-xl p-5">
              <h3 className="text-lg font-semibold text-red-400 mb-2">Rising Spending Alerts</h3>
              {data.alert_categories.map((a, i) => (
                <div key={i} className="flex justify-between items-center bg-gray-800 rounded-lg px-4 py-2 mb-2">
                  <span className="capitalize">{a.category}</span>
                  <span className="text-red-400 font-semibold">+{a.pct_change.toFixed(0)}%</span>
                </div>
              ))}
            </div>
          )}

          {/* Category Forecasts */}
          <div className="grid md:grid-cols-2 gap-6">
            {data.category_forecasts.map((cf, idx) => {
              const chartData = cf.months.map((m, i) => ({
                month: m,
                predicted: cf.predicted[i],
                lower: cf.lower_bound[i],
                upper: cf.upper_bound[i],
              }));

              return (
                <div key={cf.category} className="bg-gray-800 rounded-xl p-5 border border-gray-700">
                  <div className="flex justify-between items-center mb-3">
                    <h4 className="font-semibold capitalize">{cf.category.replace("_", " ")}</h4>
                    <span className={`text-sm font-semibold ${trendColor[cf.trend]}`}>
                      {cf.pct_change > 0 ? "+" : ""}{cf.pct_change}% ({trendIcon[cf.trend]})
                    </span>
                  </div>
                  <ResponsiveContainer width="100%" height={200}>
                    <AreaChart data={chartData}>
                      <XAxis dataKey="month" stroke="#9ca3af" tick={{ fontSize: 10 }} />
                      <YAxis stroke="#9ca3af" tickFormatter={(v) => `$${v}`} />
                      <Tooltip formatter={(v) => fmt(v)} />
                      <Area type="monotone" dataKey="upper" stroke="none" fill={COLORS[idx % COLORS.length]} fillOpacity={0.1} />
                      <Area type="monotone" dataKey="lower" stroke="none" fill={COLORS[idx % COLORS.length]} fillOpacity={0.1} />
                      <Line type="monotone" dataKey="predicted" stroke={COLORS[idx % COLORS.length]} strokeWidth={2} dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              );
            })}
          </div>

          {/* Overall trend */}
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700 text-center">
            <span className="text-gray-400">Overall expense trend: </span>
            <span className={`font-bold ${trendColor[data.overall_expense_trend]}`}>
              {data.overall_expense_trend.toUpperCase()}
            </span>
          </div>
        </>
      )}
    </div>
  );
}

import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, Legend,
} from "recharts";
import { runScenarios } from "../api";

export default function Scenarios() {
  const [data, setData] = useState(null);
  const [windfall, setWindfall] = useState(0);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    try {
      const r = await runScenarios({
        extra_amounts: [0, 50, 100, 200, 300, 500],
        windfall: parseFloat(windfall) || 0,
        windfall_target: "highest_interest",
      });
      setData(r.data);
    } catch {
      setData(null);
    }
    setLoading(false);
  };

  const fmt = (n) => `$${Number(n).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

  // Chart data: compare top scenarios
  const chartData = data?.slice(0, 8).map((s) => ({
    name: s.name.length > 25 ? s.name.slice(0, 25) + "..." : s.name,
    months: s.total_months,
    interest: s.total_interest,
    saved: s.interest_saved_vs_minimum,
  })) || [];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Scenario Optimizer</h2>
      <p className="text-gray-400">
        Compare dozens of payoff strategies side-by-side. Find your fastest path to debt freedom.
      </p>

      <div className="flex gap-4 items-end">
        <div>
          <label className="text-sm text-gray-400 block mb-1">One-time windfall ($)</label>
          <input
            type="number" step="100" value={windfall}
            onChange={(e) => setWindfall(e.target.value)}
            className="bg-gray-700 rounded-lg px-3 py-2 text-sm w-32"
            placeholder="0"
          />
        </div>
        <button
          onClick={run} disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg px-6 py-2 text-sm font-semibold transition-colors"
        >
          {loading ? "Calculating..." : "Run All Scenarios"}
        </button>
      </div>

      {data && data.length > 0 && (
        <>
          {/* Best scenario highlight */}
          <div className="bg-emerald-900/30 border border-emerald-700 rounded-xl p-5">
            <h3 className="text-lg font-semibold text-emerald-400 mb-2">Best Strategy</h3>
            <p className="text-white text-xl font-bold">{data[0].name}</p>
            <div className="grid grid-cols-3 gap-4 mt-3">
              <div>
                <p className="text-gray-400 text-xs">Months</p>
                <p className="text-lg font-bold">{data[0].total_months}</p>
              </div>
              <div>
                <p className="text-gray-400 text-xs">Total Interest</p>
                <p className="text-lg font-bold text-red-400">{fmt(data[0].total_interest)}</p>
              </div>
              <div>
                <p className="text-gray-400 text-xs">Interest Saved</p>
                <p className="text-lg font-bold text-emerald-400">{fmt(data[0].interest_saved_vs_minimum)}</p>
              </div>
            </div>
          </div>

          {/* Chart */}
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            <h3 className="text-lg font-semibold mb-4">Months to Payoff by Strategy</h3>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 120 }}>
                <XAxis type="number" stroke="#9ca3af" />
                <YAxis type="category" dataKey="name" stroke="#9ca3af" tick={{ fontSize: 11 }} width={120} />
                <Tooltip formatter={(v, name) => name === "interest" ? fmt(v) : v} />
                <Legend />
                <Bar dataKey="months" name="Months" radius={[0, 4, 4, 0]}>
                  {chartData.map((_, i) => (
                    <Cell key={i} fill={i === 0 ? "#10b981" : i < 3 ? "#3b82f6" : "#6b7280"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Full table */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-700">
                <tr>
                  <th className="px-4 py-3 text-left">Strategy</th>
                  <th className="px-4 py-3 text-right">Months</th>
                  <th className="px-4 py-3 text-right">Extra/Mo</th>
                  <th className="px-4 py-3 text-right">Total Interest</th>
                  <th className="px-4 py-3 text-right">Total Paid</th>
                  <th className="px-4 py-3 text-right">Months Saved</th>
                  <th className="px-4 py-3 text-right">Interest Saved</th>
                </tr>
              </thead>
              <tbody>
                {data.map((s, i) => (
                  <tr key={i} className={`border-t border-gray-700 ${i === 0 ? "bg-emerald-900/10" : "hover:bg-gray-750"}`}>
                    <td className="px-4 py-2">{s.name}</td>
                    <td className="px-4 py-2 text-right font-semibold">{s.total_months}</td>
                    <td className="px-4 py-2 text-right">{fmt(s.extra_monthly)}</td>
                    <td className="px-4 py-2 text-right text-red-400">{fmt(s.total_interest)}</td>
                    <td className="px-4 py-2 text-right">{fmt(s.total_paid)}</td>
                    <td className="px-4 py-2 text-right text-emerald-400">{s.months_saved_vs_minimum}</td>
                    <td className="px-4 py-2 text-right text-emerald-400">{fmt(s.interest_saved_vs_minimum)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

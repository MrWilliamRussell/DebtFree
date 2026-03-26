import { useEffect, useState } from "react";
import { getSubscriptions, getWasteAnalysis } from "../api";

const actionColors = {
  cancel: "bg-red-600",
  downgrade: "bg-yellow-600",
  negotiate: "bg-blue-600",
  keep: "bg-emerald-600",
};

const difficultyColors = {
  easy: "text-emerald-400",
  medium: "text-yellow-400",
  hard: "text-red-400",
  unknown: "text-gray-400",
};

export default function Subscriptions() {
  const [subs, setSubs] = useState([]);
  const [waste, setWaste] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    getSubscriptions({}).then((r) => setSubs(r.data)).catch(() => {});
  }, []);

  const runWasteAnalysis = async () => {
    setLoading(true);
    try {
      const r = await getWasteAnalysis();
      setWaste(r.data);
    } catch {
      setWaste(null);
    }
    setLoading(false);
  };

  const fmt = (n) => `$${Number(n).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

  const scoreColor = (score) => {
    if (score >= 70) return "bg-red-600";
    if (score >= 50) return "bg-yellow-600";
    return "bg-emerald-600";
  };

  const totalMonthly = subs.reduce((sum, s) => sum + s.avg_amount, 0);
  const totalCancellable = subs.filter((s) => s.action === "cancel").reduce((sum, s) => sum + s.avg_amount, 0);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Subscription Tracker</h2>

      {/* Summary cards */}
      {subs.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <p className="text-gray-400 text-sm">Active Subscriptions</p>
            <p className="text-2xl font-bold">{subs.length}</p>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <p className="text-gray-400 text-sm">Monthly Cost</p>
            <p className="text-2xl font-bold text-red-400">{fmt(totalMonthly)}</p>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <p className="text-gray-400 text-sm">Potential Savings</p>
            <p className="text-2xl font-bold text-emerald-400">{fmt(totalCancellable)}<span className="text-sm text-gray-400">/mo</span></p>
          </div>
        </div>
      )}

      <button
        onClick={runWasteAnalysis}
        disabled={loading}
        className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg px-6 py-2 text-sm font-semibold transition-colors"
      >
        {loading ? "Analyzing with AI..." : "Run Deep AI Analysis"}
      </button>

      {/* Subscription cards */}
      {subs.length > 0 ? (
        <div className="space-y-3">
          {subs.map((s, i) => (
            <div key={i} className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
              <div
                className="p-5 cursor-pointer hover:bg-gray-750 transition-colors"
                onClick={() => setExpanded(expanded === i ? null : i)}
              >
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    {s.action && (
                      <span className={`text-xs font-bold uppercase px-2 py-1 rounded ${actionColors[s.action] || "bg-gray-600"}`}>
                        {s.action}
                      </span>
                    )}
                    <div>
                      <h3 className="font-semibold capitalize">{s.merchant}</h3>
                      <p className="text-gray-400 text-sm capitalize">{s.category.replace("_", " ")}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-red-400">{fmt(s.avg_amount)}<span className="text-xs text-gray-400">/mo</span></p>
                    <p className="text-xs text-gray-500">{fmt(s.annual_cost)}/yr</p>
                  </div>
                </div>

                {/* Waste score bar */}
                <div className="mt-3">
                  <div className="flex justify-between text-xs text-gray-400 mb-1">
                    <span>Waste Score</span>
                    <span>{s.waste_score}/100</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div className={`h-2 rounded-full ${scoreColor(s.waste_score)}`} style={{ width: `${s.waste_score}%` }} />
                  </div>
                </div>
              </div>

              {/* Expanded details */}
              {expanded === i && (
                <div className="border-t border-gray-700 p-5 bg-gray-850 space-y-3">
                  <p className="text-sm text-gray-300">{s.suggestion}</p>

                  {s.cancel_method && (
                    <div className="bg-gray-700 rounded-lg p-3">
                      <p className="text-xs text-gray-400 mb-1">
                        How to cancel (
                        <span className={difficultyColors[s.cancel_difficulty]}>
                          {s.cancel_difficulty} difficulty
                        </span>
                        )
                      </p>
                      <p className="text-sm text-gray-200">{s.cancel_method}</p>
                    </div>
                  )}

                  {s.alternatives && (
                    <div className="bg-gray-700 rounded-lg p-3">
                      <p className="text-xs text-gray-400 mb-1">Free / Cheaper Alternatives</p>
                      <p className="text-sm text-emerald-400">{s.alternatives}</p>
                    </div>
                  )}

                  <div className="text-xs text-gray-500 flex gap-4">
                    <span>{s.occurrence_count} charges detected</span>
                    <span>Every ~{s.frequency_days} days</span>
                    <span>Total spent: {fmt(s.total_spent)}</span>
                    <span>Last: {s.last_charged}</span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-gray-500 text-center py-8">No recurring subscriptions detected yet. Import more transaction history.</p>
      )}

      {/* AI Deep Analysis */}
      {waste?.analysis && (
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700 space-y-4">
          <h3 className="text-lg font-semibold">AI Analysis</h3>
          {waste.analysis.summary && (
            <p className="text-gray-300 bg-gray-700 rounded-lg p-4">{waste.analysis.summary}</p>
          )}
          {waste.analysis.total_monthly_savings > 0 && (
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-emerald-900/30 border border-emerald-700 rounded-lg p-4">
                <p className="text-gray-400 text-xs">Monthly Savings if You Act</p>
                <p className="text-2xl font-bold text-emerald-400">{fmt(waste.analysis.total_monthly_savings)}</p>
              </div>
              {waste.analysis.debt_freedom_impact_months > 0 && (
                <div className="bg-blue-900/30 border border-blue-700 rounded-lg p-4">
                  <p className="text-gray-400 text-xs">Months Closer to Debt-Free</p>
                  <p className="text-2xl font-bold text-blue-400">{waste.analysis.debt_freedom_impact_months}</p>
                </div>
              )}
            </div>
          )}

          {waste.analysis.recommendations?.length > 0 && (
            <div className="space-y-2">
              {waste.analysis.recommendations.map((r, i) => (
                <div key={i} className="bg-gray-700 rounded-lg p-3 flex justify-between items-center">
                  <div>
                    <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded mr-2 ${actionColors[r.action] || "bg-gray-600"}`}>
                      {r.action}
                    </span>
                    <span className="font-semibold capitalize">{r.merchant}</span>
                    <p className="text-sm text-gray-400 mt-1">{r.reason}</p>
                    {r.negotiation_script && (
                      <p className="text-xs text-blue-400 mt-1">Script: "{r.negotiation_script}"</p>
                    )}
                  </div>
                  <span className="text-emerald-400 font-semibold whitespace-nowrap">
                    Save {fmt(r.savings_if_cancelled)}/mo
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

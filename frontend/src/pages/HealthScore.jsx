import { useEffect, useState } from "react";
import { getHealthScore, getCoachingNudge, submitFeedback } from "../api";

const gradeColors = {
  A: "text-emerald-400",
  B: "text-blue-400",
  C: "text-yellow-400",
  D: "text-orange-400",
  F: "text-red-400",
};

export default function HealthScore() {
  const [score, setScore] = useState(null);
  const [nudge, setNudge] = useState(null);
  const [nudgeLoading, setNudgeLoading] = useState(false);

  useEffect(() => {
    getHealthScore().then((r) => setScore(r.data)).catch(() => {});
  }, []);

  const fetchNudge = async () => {
    setNudgeLoading(true);
    try {
      const r = await getCoachingNudge();
      setNudge(r.data);
    } catch {
      setNudge({ message: "Coach unavailable — make sure Ollama is running." });
    }
    setNudgeLoading(false);
  };

  const handleFeedback = async (isPositive) => {
    if (!nudge) return;
    await submitFeedback({
      entity_type: "nudge",
      original_value: nudge.message,
      is_positive: isPositive,
    });
  };

  if (!score) {
    return <p className="text-gray-400 py-10">Loading health score...</p>;
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Financial Health Score</h2>

      {/* Big score display */}
      <div className="bg-gray-800 rounded-xl p-8 border border-gray-700 text-center">
        <div className="relative inline-flex items-center justify-center">
          <svg className="w-40 h-40" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="54" fill="none" stroke="#374151" strokeWidth="8" />
            <circle
              cx="60" cy="60" r="54" fill="none"
              stroke={score.grade === "A" ? "#10b981" : score.grade === "B" ? "#3b82f6" : score.grade === "C" ? "#f59e0b" : score.grade === "D" ? "#f97316" : "#ef4444"}
              strokeWidth="8"
              strokeDasharray={`${score.overall_score * 3.39} 339`}
              strokeLinecap="round"
              transform="rotate(-90 60 60)"
            />
          </svg>
          <div className="absolute">
            <p className={`text-4xl font-bold ${gradeColors[score.grade]}`}>{score.overall_score}</p>
            <p className="text-gray-400 text-sm">/ 100</p>
          </div>
        </div>
        <p className={`text-3xl font-bold mt-4 ${gradeColors[score.grade]}`}>Grade: {score.grade}</p>
        <p className="text-gray-400 mt-1 capitalize">Trend: {score.trend}</p>
      </div>

      {/* Component breakdown */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Object.entries(score.components).map(([name, comp]) => (
          <div key={name} className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            <div className="flex justify-between items-center mb-2">
              <h4 className="font-semibold capitalize text-sm">{name.replace("_", " ")}</h4>
              <span className="text-xs text-gray-400">{(comp.weight * 100).toFixed(0)}% weight</span>
            </div>
            <p className="text-2xl font-bold">{comp.score}<span className="text-sm text-gray-400">/100</span></p>
            <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
              <div
                className={`h-2 rounded-full ${comp.score >= 70 ? "bg-emerald-500" : comp.score >= 40 ? "bg-yellow-500" : "bg-red-500"}`}
                style={{ width: `${comp.score}%` }}
              />
            </div>
            <p className="text-xs text-gray-400 mt-2">{comp.detail}</p>
          </div>
        ))}
      </div>

      {/* Tips */}
      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
        <h3 className="text-lg font-semibold mb-3">Action Items</h3>
        <ul className="space-y-2">
          {score.tips.map((tip, i) => (
            <li key={i} className="flex gap-3 text-sm">
              <span className="text-emerald-400 font-bold">{i + 1}.</span>
              <span className="text-gray-300">{tip}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* AI Coach */}
      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-lg font-semibold">AI Coach</h3>
          <button
            onClick={fetchNudge}
            disabled={nudgeLoading}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg px-4 py-2 text-sm font-semibold transition-colors"
          >
            {nudgeLoading ? "Thinking..." : "Get Today's Nudge"}
          </button>
        </div>
        {nudge && (
          <div className="bg-gray-700 rounded-lg p-4">
            <p className="text-gray-200">{nudge.message}</p>
            <div className="flex gap-2 mt-3">
              <button onClick={() => handleFeedback(true)} className="text-sm text-emerald-400 hover:underline">Helpful</button>
              <button onClick={() => handleFeedback(false)} className="text-sm text-red-400 hover:underline">Not helpful</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

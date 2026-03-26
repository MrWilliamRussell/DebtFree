import { useState } from "react";
import { downloadReport } from "../api";

export default function Reports() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleDownload = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await downloadReport();
      const url = URL.createObjectURL(new Blob([r.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `debtfree-report-${new Date().toISOString().slice(0, 10)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError("Failed to generate report. Make sure you have data entered.");
    }
    setLoading(false);
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <h2 className="text-2xl font-bold">Monthly Reports</h2>
      <p className="text-gray-400">
        Generate a beautiful PDF summary of your financial progress. Share with an accountability partner or keep for your records.
      </p>

      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <h3 className="font-semibold mb-3">Monthly Progress Report</h3>
        <p className="text-sm text-gray-400 mb-4">Includes:</p>
        <ul className="text-sm text-gray-400 space-y-1 mb-6 list-disc list-inside">
          <li>Income vs expenses summary</li>
          <li>Expenses by category pie chart</li>
          <li>Health score and grade</li>
          <li>Debt status and payoff progress</li>
          <li>Personalized action items</li>
        </ul>
        <button
          onClick={handleDownload}
          disabled={loading}
          className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg px-6 py-3 text-sm font-semibold transition-colors"
        >
          {loading ? "Generating PDF..." : "Download Monthly Report"}
        </button>
        {error && (
          <p className="text-red-400 text-sm mt-3">{error}</p>
        )}
      </div>

      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <h3 className="font-semibold mb-3">Coming Soon</h3>
        <ul className="text-sm text-gray-400 space-y-2">
          <li>Before vs After comparison reports</li>
          <li>Annual year-in-review summary</li>
          <li>Shareable debt-free celebration card</li>
          <li>Email/Discord scheduled reports</li>
        </ul>
      </div>
    </div>
  );
}

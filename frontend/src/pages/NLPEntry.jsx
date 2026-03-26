import { useState, useEffect } from "react";
import { parseNLP, parseAndSaveNLP, getAccounts } from "../api";

export default function NLPEntry() {
  const [text, setText] = useState("");
  const [accountId, setAccountId] = useState("");
  const [accounts, setAccounts] = useState([]);
  const [preview, setPreview] = useState(null);
  const [saved, setSaved] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getAccounts().then((r) => setAccounts(r.data));
  }, []);

  const handlePreview = async () => {
    if (!text || !accountId) return;
    setLoading(true);
    setSaved(null);
    try {
      const r = await parseNLP({ text, account_id: parseInt(accountId) });
      setPreview(r.data);
    } catch (err) {
      setPreview({ error: err.response?.data?.detail || "Parse failed" });
    }
    setLoading(false);
  };

  const handleSave = async () => {
    if (!text || !accountId) return;
    setLoading(true);
    try {
      const r = await parseAndSaveNLP({ text, account_id: parseInt(accountId) });
      setSaved(r.data);
      setPreview(null);
      setText("");
    } catch (err) {
      setSaved({ error: err.response?.data?.detail || "Save failed" });
    }
    setLoading(false);
  };

  const fmt = (n) => `$${Number(n).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

  const confidenceColor = {
    high: "text-emerald-400",
    medium: "text-yellow-400",
    low: "text-red-400",
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <h2 className="text-2xl font-bold">Quick Entry</h2>
      <p className="text-gray-400">
        Type or speak naturally. The AI parses your input into a structured transaction.
      </p>

      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 space-y-4">
        <div>
          <label className="text-sm text-gray-400 block mb-1">Account</label>
          <select
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
            className="bg-gray-700 rounded-lg px-3 py-2 text-sm w-full"
            required
          >
            <option value="">Select account...</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-sm text-gray-400 block mb-1">Describe the transaction</label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder='e.g. "Spent $45 on gas yesterday at Shell" or "Netflix $15.99 monthly subscription"'
            className="bg-gray-700 rounded-lg px-3 py-3 text-sm w-full h-24 resize-none"
          />
        </div>

        <div className="flex gap-3">
          <button
            onClick={handlePreview}
            disabled={loading || !text || !accountId}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg px-4 py-2 text-sm font-semibold transition-colors"
          >
            {loading ? "Parsing..." : "Preview"}
          </button>
          <button
            onClick={handleSave}
            disabled={loading || !text || !accountId}
            className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg px-4 py-2 text-sm font-semibold transition-colors"
          >
            Save Directly
          </button>
        </div>
      </div>

      {/* Preview */}
      {preview && !preview.error && (
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700 space-y-3">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold">Parsed Result</h3>
            <span className={`text-sm font-semibold ${confidenceColor[preview.confidence]}`}>
              {preview.confidence} confidence
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            {Object.entries(preview.parsed).map(([key, val]) => (
              <div key={key} className="bg-gray-700 rounded-lg px-3 py-2">
                <span className="text-gray-400">{key}: </span>
                <span className="font-semibold">
                  {key === "amount" ? fmt(val) : String(val)}
                </span>
              </div>
            ))}
          </div>
          {preview.needs_review && (
            <p className="text-yellow-400 text-sm">Review recommended before saving.</p>
          )}
          <button
            onClick={handleSave}
            className="bg-emerald-600 hover:bg-emerald-700 rounded-lg px-4 py-2 text-sm font-semibold transition-colors"
          >
            Confirm & Save
          </button>
        </div>
      )}

      {preview?.error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-4">
          <p className="text-red-400">{preview.error}</p>
        </div>
      )}

      {saved && !saved.error && (
        <div className="bg-emerald-900/30 border border-emerald-700 rounded-lg p-4">
          <p className="text-emerald-400">
            Saved: {saved.description} — {fmt(saved.amount)} ({saved.category})
          </p>
        </div>
      )}

      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
        <h3 className="font-semibold mb-2">Example inputs</h3>
        <ul className="text-sm text-gray-400 space-y-1">
          <li>"Spent $45 on gas yesterday at Shell"</li>
          <li>"Amazon earbuds $67"</li>
          <li>"Costco groceries $142.50 last Saturday"</li>
          <li>"Netflix $15.99 monthly subscription"</li>
          <li>"Got paid $3,200 from work today"</li>
          <li>"Rent $1,800 on the 1st, recurring"</li>
        </ul>
      </div>
    </div>
  );
}

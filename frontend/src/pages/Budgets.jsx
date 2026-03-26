import { useEffect, useState } from "react";
import { getBudgets, createBudget } from "../api";

const CATEGORIES = [
  "rent", "mortgage", "utilities", "groceries", "gas", "insurance", "medical",
  "dining", "entertainment", "shopping", "amazon", "subscriptions", "clothing",
  "travel", "debt_payment", "savings", "investment", "other",
];

export default function Budgets() {
  const [budgets, setBudgets] = useState([]);
  const [form, setForm] = useState({ category: "groceries", monthly_limit: "", alert_threshold: "0.80" });

  const load = () => getBudgets().then((r) => setBudgets(r.data));
  useEffect(load, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    await createBudget({
      ...form,
      monthly_limit: parseFloat(form.monthly_limit),
      alert_threshold: parseFloat(form.alert_threshold),
    });
    setForm({ category: "groceries", monthly_limit: "", alert_threshold: "0.80" });
    load();
  };

  const fmt = (n) => `$${Number(n).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Budgets</h2>
      <p className="text-gray-400">Set monthly limits per category. Discord alerts fire when spending hits the threshold.</p>

      <form onSubmit={handleAdd} className="bg-gray-800 rounded-xl p-5 border border-gray-700 flex gap-3 items-end flex-wrap">
        <div>
          <label className="text-sm text-gray-400 block mb-1">Category</label>
          <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm">
            {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace("_", " ")}</option>)}
          </select>
        </div>
        <div>
          <label className="text-sm text-gray-400 block mb-1">Monthly Limit</label>
          <input placeholder="500" type="number" step="10" value={form.monthly_limit} onChange={(e) => setForm({ ...form, monthly_limit: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm w-32" required />
        </div>
        <div>
          <label className="text-sm text-gray-400 block mb-1">Alert at %</label>
          <input type="number" step="0.05" min="0" max="1" value={form.alert_threshold} onChange={(e) => setForm({ ...form, alert_threshold: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm w-24" />
        </div>
        <button type="submit" className="bg-emerald-600 hover:bg-emerald-700 rounded-lg px-4 py-2 text-sm font-semibold transition-colors">Add Budget</button>
      </form>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {budgets.map((b) => (
          <div key={b.id} className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            <h3 className="font-semibold capitalize">{b.category.replace("_", " ")}</h3>
            <p className="text-2xl font-bold text-emerald-400 mt-1">{fmt(b.monthly_limit)}<span className="text-sm text-gray-400">/mo</span></p>
            <p className="text-sm text-gray-400 mt-1">Alert at {(b.alert_threshold * 100).toFixed(0)}%</p>
          </div>
        ))}
        {budgets.length === 0 && (
          <p className="text-gray-500 col-span-3 text-center py-8">No budgets set. Add limits above to get Discord alerts.</p>
        )}
      </div>
    </div>
  );
}

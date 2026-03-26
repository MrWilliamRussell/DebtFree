import { useEffect, useState } from "react";
import { getAccounts, createAccount } from "../api";

const ACCOUNT_TYPES = ["checking", "savings", "credit_card", "loan", "investment", "cash"];

export default function Accounts() {
  const [accounts, setAccounts] = useState([]);
  const [form, setForm] = useState({
    name: "", account_type: "checking", institution: "", balance: "",
    interest_rate: "", credit_limit: "", minimum_payment: "", due_day: 1,
  });

  const load = () => getAccounts().then((r) => setAccounts(r.data));
  useEffect(load, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    await createAccount({
      ...form,
      balance: parseFloat(form.balance) || 0,
      interest_rate: parseFloat(form.interest_rate) || 0,
      credit_limit: form.credit_limit ? parseFloat(form.credit_limit) : null,
      minimum_payment: parseFloat(form.minimum_payment) || 0,
      due_day: parseInt(form.due_day) || 1,
    });
    setForm({ name: "", account_type: "checking", institution: "", balance: "", interest_rate: "", credit_limit: "", minimum_payment: "", due_day: 1 });
    load();
  };

  const fmt = (n) => `$${Number(n).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Accounts</h2>

      <form onSubmit={handleAdd} className="bg-gray-800 rounded-xl p-5 border border-gray-700 grid grid-cols-2 md:grid-cols-4 gap-3">
        <input placeholder="Account Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm" required />
        <select value={form.account_type} onChange={(e) => setForm({ ...form, account_type: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm">
          {ACCOUNT_TYPES.map((t) => <option key={t} value={t}>{t.replace("_", " ")}</option>)}
        </select>
        <input placeholder="Institution" value={form.institution} onChange={(e) => setForm({ ...form, institution: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm" />
        <input placeholder="Balance" type="number" step="0.01" value={form.balance} onChange={(e) => setForm({ ...form, balance: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm" />
        <input placeholder="APR %" type="number" step="0.01" value={form.interest_rate} onChange={(e) => setForm({ ...form, interest_rate: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm" />
        <input placeholder="Credit Limit" type="number" step="0.01" value={form.credit_limit} onChange={(e) => setForm({ ...form, credit_limit: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm" />
        <input placeholder="Min Payment" type="number" step="0.01" value={form.minimum_payment} onChange={(e) => setForm({ ...form, minimum_payment: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm" />
        <button type="submit" className="bg-emerald-600 hover:bg-emerald-700 rounded-lg px-4 py-2 text-sm font-semibold transition-colors">Add Account</button>
      </form>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {accounts.map((a) => (
          <div key={a.id} className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="font-semibold">{a.name}</h3>
                <p className="text-gray-400 text-sm capitalize">{a.account_type.replace("_", " ")} — {a.institution}</p>
              </div>
              <span className={`text-lg font-bold ${a.account_type === "credit_card" || a.account_type === "loan" ? "text-red-400" : "text-emerald-400"}`}>
                {fmt(a.balance)}
              </span>
            </div>
            {a.interest_rate > 0 && <p className="text-sm text-gray-400 mt-2">APR: {a.interest_rate}%</p>}
            {a.credit_limit && <p className="text-sm text-gray-400">Limit: {fmt(a.credit_limit)}</p>}
            {a.minimum_payment > 0 && <p className="text-sm text-gray-400">Min payment: {fmt(a.minimum_payment)}</p>}
          </div>
        ))}
        {accounts.length === 0 && (
          <p className="text-gray-500 col-span-3 text-center py-8">No accounts yet. Add your bank accounts and credit cards above.</p>
        )}
      </div>
    </div>
  );
}

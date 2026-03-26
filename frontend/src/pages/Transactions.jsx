import { useEffect, useState } from "react";
import { getTransactions, createTransaction, getAccounts } from "../api";

const CATEGORIES = [
  "rent", "mortgage", "utilities", "groceries", "gas", "insurance", "medical",
  "dining", "entertainment", "shopping", "amazon", "subscriptions", "clothing",
  "travel", "debt_payment", "savings", "investment", "income", "transfer", "other",
];

export default function Transactions() {
  const [transactions, setTransactions] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [form, setForm] = useState({
    account_id: "", date: new Date().toISOString().slice(0, 10),
    amount: "", transaction_type: "expense", category: "other",
    description: "", merchant: "", is_essential: false,
  });

  const load = () => {
    getTransactions({}).then((r) => setTransactions(r.data));
    getAccounts().then((r) => setAccounts(r.data));
  };

  useEffect(load, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    await createTransaction({
      ...form,
      account_id: parseInt(form.account_id),
      amount: parseFloat(form.amount),
    });
    setForm({ ...form, amount: "", description: "", merchant: "" });
    load();
  };

  const fmt = (n) => `$${Number(n).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Transactions</h2>

      {/* Add form */}
      <form onSubmit={handleAdd} className="bg-gray-800 rounded-xl p-5 border border-gray-700 grid grid-cols-2 md:grid-cols-4 gap-3">
        <select value={form.account_id} onChange={(e) => setForm({ ...form, account_id: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm" required>
          <option value="">Select Account</option>
          {accounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm" required />
        <input placeholder="Amount" type="number" step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm" required />
        <select value={form.transaction_type} onChange={(e) => setForm({ ...form, transaction_type: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm">
          <option value="expense">Expense</option>
          <option value="income">Income</option>
          <option value="transfer">Transfer</option>
        </select>
        <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm">
          {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace("_", " ")}</option>)}
        </select>
        <input placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm col-span-2" />
        <button type="submit" className="bg-emerald-600 hover:bg-emerald-700 rounded-lg px-4 py-2 text-sm font-semibold transition-colors">Add</button>
      </form>

      {/* Transaction list */}
      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-700">
            <tr>
              <th className="px-4 py-3 text-left">Date</th>
              <th className="px-4 py-3 text-left">Description</th>
              <th className="px-4 py-3 text-left">Category</th>
              <th className="px-4 py-3 text-right">Amount</th>
              <th className="px-4 py-3 text-center">Type</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((t) => (
              <tr key={t.id} className="border-t border-gray-700 hover:bg-gray-750">
                <td className="px-4 py-2">{t.date}</td>
                <td className="px-4 py-2">{t.description}</td>
                <td className="px-4 py-2 capitalize">{t.category.replace("_", " ")}</td>
                <td className={`px-4 py-2 text-right font-semibold ${t.transaction_type === "income" ? "text-emerald-400" : "text-red-400"}`}>
                  {t.transaction_type === "income" ? "+" : "-"}{fmt(t.amount)}
                </td>
                <td className="px-4 py-2 text-center capitalize">{t.transaction_type}</td>
              </tr>
            ))}
            {transactions.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">No transactions yet</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

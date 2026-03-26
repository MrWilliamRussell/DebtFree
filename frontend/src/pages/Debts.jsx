import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { getDebts, createDebt, getPayoffPlan } from "../api";

export default function Debts() {
  const [debts, setDebts] = useState([]);
  const [plan, setPlan] = useState(null);
  const [strategy, setStrategy] = useState("avalanche");
  const [extraPayment, setExtraPayment] = useState(0);
  const [form, setForm] = useState({
    name: "", current_balance: "", interest_rate: "", minimum_payment: "", due_day: 1,
  });

  const loadDebts = () => getDebts().then((r) => setDebts(r.data));

  useEffect(() => { loadDebts(); }, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    await createDebt({
      ...form,
      current_balance: parseFloat(form.current_balance),
      interest_rate: parseFloat(form.interest_rate),
      minimum_payment: parseFloat(form.minimum_payment),
      due_day: parseInt(form.due_day),
    });
    setForm({ name: "", current_balance: "", interest_rate: "", minimum_payment: "", due_day: 1 });
    loadDebts();
  };

  const runPlan = async () => {
    const r = await getPayoffPlan({ strategy, extra_monthly_payment: parseFloat(extraPayment) || 0 });
    setPlan(r.data);
  };

  // Build chart data from payoff plan (monthly totals per debt)
  const chartData = plan
    ? (() => {
        const byMonth = {};
        plan.monthly_plan.forEach((step) => {
          if (!byMonth[step.month]) byMonth[step.month] = { month: step.month };
          byMonth[step.month][step.debt_name] = step.remaining_balance;
        });
        return Object.values(byMonth);
      })()
    : [];

  const fmt = (n) => `$${Number(n).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;
  const COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Debt Management</h2>

      {/* Add Debt Form */}
      <form onSubmit={handleAdd} className="bg-gray-800 rounded-xl p-5 border border-gray-700 grid grid-cols-2 md:grid-cols-5 gap-3">
        <input placeholder="Name (e.g. Chase Visa)" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm" required />
        <input placeholder="Balance" type="number" step="0.01" value={form.current_balance} onChange={(e) => setForm({ ...form, current_balance: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm" required />
        <input placeholder="APR %" type="number" step="0.01" value={form.interest_rate} onChange={(e) => setForm({ ...form, interest_rate: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm" required />
        <input placeholder="Min Payment" type="number" step="0.01" value={form.minimum_payment} onChange={(e) => setForm({ ...form, minimum_payment: e.target.value })} className="bg-gray-700 rounded-lg px-3 py-2 text-sm" required />
        <button type="submit" className="bg-emerald-600 hover:bg-emerald-700 rounded-lg px-4 py-2 text-sm font-semibold transition-colors">Add Debt</button>
      </form>

      {/* Debts table */}
      {debts.length > 0 && (
        <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-700">
              <tr>
                <th className="px-4 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-right">Balance</th>
                <th className="px-4 py-3 text-right">APR</th>
                <th className="px-4 py-3 text-right">Min Payment</th>
                <th className="px-4 py-3 text-right">Due Day</th>
              </tr>
            </thead>
            <tbody>
              {debts.map((d) => (
                <tr key={d.id} className="border-t border-gray-700 hover:bg-gray-750">
                  <td className="px-4 py-3">{d.name}</td>
                  <td className="px-4 py-3 text-right text-red-400">{fmt(d.current_balance)}</td>
                  <td className="px-4 py-3 text-right">{d.interest_rate}%</td>
                  <td className="px-4 py-3 text-right">{fmt(d.minimum_payment)}</td>
                  <td className="px-4 py-3 text-right">{d.due_day}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Payoff Planner */}
      {debts.length > 0 && (
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700 space-y-4">
          <h3 className="text-lg font-semibold">Payoff Planner</h3>
          <div className="flex gap-4 items-end">
            <div>
              <label className="text-sm text-gray-400 block mb-1">Strategy</label>
              <select value={strategy} onChange={(e) => setStrategy(e.target.value)} className="bg-gray-700 rounded-lg px-3 py-2 text-sm">
                <option value="avalanche">Avalanche (highest interest first)</option>
                <option value="snowball">Snowball (smallest balance first)</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-gray-400 block mb-1">Extra $/month</label>
              <input type="number" step="10" value={extraPayment} onChange={(e) => setExtraPayment(e.target.value)} className="bg-gray-700 rounded-lg px-3 py-2 text-sm w-32" />
            </div>
            <button onClick={runPlan} className="bg-blue-600 hover:bg-blue-700 rounded-lg px-4 py-2 text-sm font-semibold transition-colors">Calculate</button>
          </div>

          {plan && (
            <div className="space-y-4 mt-4">
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gray-700 rounded-lg p-3">
                  <p className="text-gray-400 text-xs">Months to Payoff</p>
                  <p className="text-xl font-bold text-emerald-400">{plan.total_months}</p>
                </div>
                <div className="bg-gray-700 rounded-lg p-3">
                  <p className="text-gray-400 text-xs">Total Interest</p>
                  <p className="text-xl font-bold text-red-400">{fmt(plan.total_interest_paid)}</p>
                </div>
                <div className="bg-gray-700 rounded-lg p-3">
                  <p className="text-gray-400 text-xs">Total Paid</p>
                  <p className="text-xl font-bold">{fmt(plan.total_paid)}</p>
                </div>
              </div>

              <div>
                <p className="text-sm text-gray-400 mb-1">Payoff order: {plan.payoff_order.join(" → ")}</p>
              </div>

              {/* Payoff Chart */}
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={chartData}>
                  <XAxis dataKey="month" stroke="#9ca3af" label={{ value: "Month", position: "insideBottom", offset: -5 }} />
                  <YAxis stroke="#9ca3af" tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v) => fmt(v)} />
                  <Legend />
                  {debts.map((d, i) => (
                    <Line key={d.id} type="monotone" dataKey={d.name} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={false} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

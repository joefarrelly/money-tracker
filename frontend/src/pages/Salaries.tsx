import { useEffect, useState } from "react";
import { getSalaries, createSalary, deleteSalary } from "../api/client";
import type { Salary } from "../types";

const emptyForm = {
  date: "",
  net_amount: "",
  gross_amount: "",
  employer: "",
  notes: "",
};

export default function Salaries() {
  const [salaries, setSalaries] = useState<Salary[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { getSalaries().then(setSalaries); }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const created = await createSalary({
        ...form,
        net_amount: parseFloat(form.net_amount),
        gross_amount: form.gross_amount ? parseFloat(form.gross_amount) : null,
      });
      setSalaries((prev) => [created, ...prev]);
      setForm(emptyForm);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    await deleteSalary(id);
    setSalaries((prev) => prev.filter((s) => s.id !== id));
  };

  const totalNet = salaries.reduce((s, r) => s + r.net_amount, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-baseline gap-4">
        <h1 className="text-lg font-semibold">Salaries / payslips</h1>
        <span className="text-sm text-gray-400">
          {salaries.length} entries · total net: <span className="text-green-400">£{totalNet.toLocaleString()}</span>
        </span>
      </div>

      {/* Add form */}
      <form onSubmit={handleSubmit} className="bg-gray-900 rounded-xl border border-gray-800 p-5 space-y-4">
        <h2 className="text-sm font-medium text-gray-300">Add payslip</h2>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <label className="text-xs text-gray-400">Date *</label>
            <input
              type="date"
              required
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              className="mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400">Net amount (£) *</label>
            <input
              type="number"
              required
              step="0.01"
              value={form.net_amount}
              onChange={(e) => setForm({ ...form, net_amount: e.target.value })}
              className="mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400">Gross amount (£)</label>
            <input
              type="number"
              step="0.01"
              value={form.gross_amount}
              onChange={(e) => setForm({ ...form, gross_amount: e.target.value })}
              className="mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400">Employer</label>
            <input
              type="text"
              value={form.employer}
              onChange={(e) => setForm({ ...form, employer: e.target.value })}
              className="mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div className="md:col-span-2">
            <label className="text-xs text-gray-400">Notes</label>
            <input
              type="text"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className="mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
            />
          </div>
        </div>
        <button
          type="submit"
          disabled={saving}
          className="bg-green-700 hover:bg-green-600 disabled:opacity-50 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          {saving ? "Saving…" : "Add payslip"}
        </button>
      </form>

      {/* Table */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-left text-gray-400">
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Employer</th>
              <th className="px-4 py-3 text-right">Gross</th>
              <th className="px-4 py-3 text-right">Net</th>
              <th className="px-4 py-3">Notes</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {salaries.map((s) => (
              <tr key={s.id} className="border-b border-gray-800/50 hover:bg-gray-800/40">
                <td className="px-4 py-3">{new Date(s.date).toLocaleDateString("en-GB")}</td>
                <td className="px-4 py-3 text-gray-300">{s.employer ?? "—"}</td>
                <td className="px-4 py-3 text-right text-gray-400">
                  {s.gross_amount != null ? `£${s.gross_amount.toLocaleString()}` : "—"}
                </td>
                <td className="px-4 py-3 text-right text-green-400 font-medium">
                  £{s.net_amount.toLocaleString()}
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">{s.notes ?? ""}</td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => handleDelete(s.id)}
                    className="text-xs text-gray-600 hover:text-red-400"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {salaries.length === 0 && (
          <p className="px-4 py-6 text-gray-500 text-sm text-center">No payslips yet.</p>
        )}
      </div>
    </div>
  );
}

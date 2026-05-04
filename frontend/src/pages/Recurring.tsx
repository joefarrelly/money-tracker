import { useEffect, useState } from "react";
import { getRecurring, syncRecurring, patchRecurring, getCategories } from "../api/client";
import type { RecurringExpense, Category } from "../types";
import { Spinner } from "../components/Spinner";

export default function Recurring() {
  const [items, setItems] = useState<RecurringExpense[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getRecurring(), getCategories()]).then(([r, c]) => {
      setItems(r);
      setCategories(c);
    }).finally(() => setLoading(false));
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const r = await syncRecurring();
      setSyncResult(`Created ${r.created}, updated ${r.updated}, skipped ${r.skipped}`);
      getRecurring().then(setItems);
    } finally {
      setSyncing(false);
    }
  };

  const confirm = async (id: number, confirmed: boolean) => {
    const updated = await patchRecurring(id, { is_confirmed: confirmed });
    setItems((prev) => prev.map((r) => (r.id === id ? updated : r)));
  };

  const deactivate = async (id: number) => {
    const updated = await patchRecurring(id, { is_active: false });
    setItems((prev) => prev.filter((r) => r.id !== updated.id));
  };

  const updateCategory = async (id: number, category_id: number | null) => {
    const updated = await patchRecurring(id, { category_id });
    setItems((prev) => prev.map((r) => (r.id === id ? updated : r)));
  };

  const monthlyTotal = items.reduce((sum, r) => sum + r.monthly_cost, 0);

  if (loading) return <Spinner />;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Recurring expenses</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Monthly total: <span className="text-red-400 font-medium">£{monthlyTotal.toFixed(2)}</span>
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            {syncing ? "Detecting…" : "Auto-detect recurring"}
          </button>
          {syncResult && <p className="text-xs text-slate-400">{syncResult}</p>}
        </div>
      </div>

      <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 text-left text-slate-400">
              <th className="px-4 py-3">Merchant</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Frequency</th>
              <th className="px-4 py-3">Monthly cost</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {items.map((r) => (
              <tr key={r.id} className="border-b border-slate-800/50 hover:bg-slate-800/40">
                <td className="px-4 py-3 font-mono text-xs">{r.merchant_pattern}</td>
                <td className="px-4 py-3 text-red-400">£{r.typical_amount.toFixed(2)}</td>
                <td className="px-4 py-3 capitalize text-slate-400">{r.frequency}</td>
                <td className="px-4 py-3 text-red-400">£{r.monthly_cost.toFixed(2)}</td>
                <td className="px-4 py-3">
                  <select
                    value={r.category_id ?? ""}
                    onChange={(e) =>
                      updateCategory(r.id, e.target.value ? Number(e.target.value) : null)
                    }
                    className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs"
                  >
                    <option value="">—</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </td>
                <td className="px-4 py-3">
                  {r.is_confirmed ? (
                    <span className="text-xs bg-green-900/40 text-green-400 px-2 py-0.5 rounded-full">
                      Confirmed
                    </span>
                  ) : (
                    <span className="text-xs bg-yellow-900/40 text-yellow-400 px-2 py-0.5 rounded-full">
                      Candidate
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    {!r.is_confirmed && (
                      <button
                        onClick={() => confirm(r.id, true)}
                        className="text-xs text-green-400 hover:underline"
                      >
                        Confirm
                      </button>
                    )}
                    <button
                      onClick={() => deactivate(r.id)}
                      className="text-xs text-slate-500 hover:text-red-400 hover:underline"
                    >
                      Remove
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && (
          <p className="px-4 py-6 text-slate-500 text-sm text-center">
            No recurring expenses yet. Upload statements then click "Auto-detect".
          </p>
        )}
      </div>
    </div>
  );
}

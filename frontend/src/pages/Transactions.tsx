import { useEffect, useState, useCallback } from "react";
import { getTransactions, patchTransaction, getCategories, getAccounts } from "../api/client";
import { Spinner } from "../components/Spinner";
import type { Category, PaginatedTransactions, Account } from "../types";

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function AmountBadge({ amount }: { amount: number }) {
  const positive = amount >= 0;
  return (
    <span className={`font-mono text-sm ${positive ? "text-green-400" : "text-red-400"}`}>
      {positive ? "+" : ""}£{Math.abs(amount).toFixed(2)}
    </span>
  );
}

export default function Transactions() {
  const [data, setData] = useState<PaginatedTransactions | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [accountFilter, setAccountFilter] = useState("");
  const [yearFilter, setYearFilter] = useState("");
  const [monthFilter, setMonthFilter] = useState("");
  const [amountType, setAmountType] = useState<"" | "in" | "out">("");
  const [hideTransfers, setHideTransfers] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    const params: Record<string, string | number> = { page, per_page: 50 };
    if (search) params.search = search;
    if (categoryFilter) params.category_id = Number(categoryFilter);
    if (accountFilter) params.account_id = Number(accountFilter);
    if (yearFilter) params.year = Number(yearFilter);
    if (monthFilter) params.month = Number(monthFilter);
    if (amountType) params.amount_type = amountType;
    if (hideTransfers) params.hide_transfers = "true";

    getTransactions(params)
      .then(setData)
      .finally(() => setLoading(false));
  }, [page, search, categoryFilter, accountFilter, yearFilter, monthFilter, amountType, hideTransfers]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    getCategories().then(setCategories);
    getAccounts().then(setAccounts);
  }, []);

  const reset = () => setPage(1);

  const updateCategory = async (id: number, category_id: number | null) => {
    const updated = await patchTransaction(id, { category_id });
    setData((prev) =>
      prev
        ? { ...prev, transactions: prev.transactions.map((t) => (t.id === id ? updated : t)) }
        : prev
    );
  };

  const clearFilters = () => {
    setSearch("");
    setCategoryFilter("");
    setAccountFilter("");
    setYearFilter("");
    setMonthFilter("");
    setAmountType("");
    setHideTransfers(false);
    setPage(1);
  };

  const hasFilters = search || categoryFilter || accountFilter || yearFilter || monthFilter || amountType || hideTransfers;

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-4 space-y-3">
        <div className="flex gap-3 flex-wrap">
          <input
            type="text"
            placeholder="Search descriptions…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); reset(); }}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm w-56"
          />
          <select
            value={categoryFilter}
            onChange={(e) => { setCategoryFilter(e.target.value); reset(); }}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm"
          >
            <option value="">All categories</option>
            <option value="-1">Uncategorised</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <select
            value={accountFilter}
            onChange={(e) => { setAccountFilter(e.target.value); reset(); }}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm"
          >
            <option value="">All accounts</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>{a.nickname ?? a.account_number}</option>
            ))}
          </select>
        </div>

        <div className="flex gap-3 flex-wrap items-center">
          <select
            value={yearFilter}
            onChange={(e) => { setYearFilter(e.target.value); reset(); }}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm"
          >
            <option value="">All years</option>
            {[2023, 2024, 2025, 2026].map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
          <select
            value={monthFilter}
            onChange={(e) => { setMonthFilter(e.target.value); reset(); }}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm"
            disabled={!yearFilter}
          >
            <option value="">All months</option>
            {MONTHS.map((m, i) => (
              <option key={i} value={i + 1}>{m}</option>
            ))}
          </select>

          <div className="flex rounded-lg overflow-hidden border border-slate-700 text-sm">
            {(["", "in", "out"] as const).map((t) => (
              <button
                key={t}
                onClick={() => { setAmountType(t); reset(); }}
                className={`px-3 py-1.5 transition-colors ${
                  amountType === t
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-800 text-slate-400 hover:bg-gray-700"
                }`}
              >
                {t === "" ? "All" : t === "in" ? "Money in" : "Money out"}
              </button>
            ))}
          </div>

          <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={hideTransfers}
              onChange={(e) => { setHideTransfers(e.target.checked); reset(); }}
              className="rounded"
            />
            Hide transfers
          </label>

          <div className="flex items-center gap-3 ml-auto">
            {hasFilters && (
              <button
                onClick={clearFilters}
                className="text-xs text-slate-500 hover:text-slate-300"
              >
                Clear filters
              </button>
            )}
            {data && (
              <span className="text-slate-400 text-sm">
                {data.total} transactions
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <Spinner />
      ) : (
        <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-slate-400">
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Description</th>
                <th className="px-4 py-3">Account</th>
                <th className="px-4 py-3 text-right">Amount</th>
                <th className="px-4 py-3">Category</th>
              </tr>
            </thead>
            <tbody>
              {data?.transactions.map((t) => (
                <tr
                  key={t.id}
                  className={`border-b border-slate-800/50 hover:bg-slate-800/40 transition-colors ${
                    t.is_transfer ? "opacity-60" : ""
                  }`}
                >
                  <td className="px-4 py-2.5 text-slate-400 whitespace-nowrap">
                    {new Date(t.date).toLocaleDateString("en-GB")}
                  </td>
                  <td className="px-4 py-2.5 max-w-xs truncate" title={t.description}>
                    {t.description}
                    {t.is_transfer && (
                      <span className="ml-2 text-xs text-slate-600 bg-slate-800 px-1.5 py-0.5 rounded">
                        transfer
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-slate-400 text-xs">
                    {t.account?.nickname ?? "—"}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <AmountBadge amount={t.amount} />
                  </td>
                  <td className="px-4 py-2.5">
                    <select
                      value={t.category_id ?? ""}
                      onChange={(e) =>
                        updateCategory(t.id, e.target.value ? Number(e.target.value) : null)
                      }
                      className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs"
                    >
                      <option value="">Uncategorised</option>
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {data?.transactions.length === 0 && (
            <p className="px-4 py-8 text-slate-500 text-sm text-center">No transactions match your filters.</p>
          )}
        </div>
      )}

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex gap-2 justify-center">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 bg-slate-800 rounded-lg text-sm disabled:opacity-40"
          >
            Previous
          </button>
          <span className="px-3 py-1.5 text-sm text-slate-400">
            {page} / {data.pages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
            disabled={page === data.pages}
            className="px-3 py-1.5 bg-slate-800 rounded-lg text-sm disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

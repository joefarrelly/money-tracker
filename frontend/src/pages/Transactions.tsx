import { useEffect, useState, useCallback } from "react";
import { getTransactions, patchTransaction, getCategories } from "../api/client";
import type { Transaction, Category, PaginatedTransactions } from "../types";

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
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    const params: Record<string, string | number> = { page, per_page: 50 };
    if (search) params.search = search;
    if (categoryFilter) params.category_id = Number(categoryFilter);

    getTransactions(params)
      .then(setData)
      .finally(() => setLoading(false));
  }, [page, search, categoryFilter]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { getCategories().then(setCategories); }, []);

  const updateCategory = async (id: number, category_id: number | null) => {
    const updated = await patchTransaction(id, { category_id });
    setData((prev) =>
      prev
        ? {
            ...prev,
            transactions: prev.transactions.map((t) => (t.id === id ? updated : t)),
          }
        : prev
    );
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <input
          type="text"
          placeholder="Search descriptions…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm w-64"
        />
        <select
          value={categoryFilter}
          onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm"
        >
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        {data && (
          <span className="text-gray-400 text-sm self-center">
            {data.total} transactions
          </span>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <p className="text-gray-400">Loading…</p>
      ) : (
        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-left text-gray-400">
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
                  className="border-b border-gray-800/50 hover:bg-gray-800/40 transition-colors"
                >
                  <td className="px-4 py-2.5 text-gray-400 whitespace-nowrap">
                    {new Date(t.date).toLocaleDateString("en-GB")}
                  </td>
                  <td className="px-4 py-2.5 max-w-xs truncate" title={t.description}>
                    {t.description}
                  </td>
                  <td className="px-4 py-2.5 text-gray-400 text-xs">
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
                      className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs"
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
        </div>
      )}

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex gap-2 justify-center">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 bg-gray-800 rounded-lg text-sm disabled:opacity-40"
          >
            Previous
          </button>
          <span className="px-3 py-1.5 text-sm text-gray-400">
            {page} / {data.pages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
            disabled={page === data.pages}
            className="px-3 py-1.5 bg-gray-800 rounded-lg text-sm disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

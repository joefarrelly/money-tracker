import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { getMonthlySummary, getTrend } from "../api/client";
import type { MonthlySummary } from "../types";

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function StatCard({
  label,
  value,
  sub,
  color = "text-white",
}: {
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
      <p className="text-sm text-gray-400">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}

export default function Dashboard() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [summary, setSummary] = useState<MonthlySummary | null>(null);
  const [trend, setTrend] = useState<MonthlySummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([getMonthlySummary(year, month), getTrend(6)])
      .then(([s, t]) => {
        setSummary(s);
        setTrend(t);
      })
      .finally(() => setLoading(false));
  }, [year, month]);

  const trendData = trend.map((m) => ({
    name: `${MONTHS[m.month - 1]} ${m.year}`,
    In: m.total_in,
    Out: m.total_out,
    Disposable: m.disposable_income,
  }));

  return (
    <div className="space-y-6">
      {/* Month picker */}
      <div className="flex items-center gap-3">
        <select
          value={month}
          onChange={(e) => setMonth(Number(e.target.value))}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm"
        >
          {MONTHS.map((m, i) => (
            <option key={m} value={i + 1}>{m}</option>
          ))}
        </select>
        <select
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm"
        >
          {[2023, 2024, 2025, 2026].map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      {loading && <p className="text-gray-400">Loading…</p>}

      {!loading && summary && (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              label="Salary (net)"
              value={`£${summary.salary.toLocaleString()}`}
              color="text-green-400"
            />
            <StatCard
              label="Recurring expenses"
              value={`£${summary.recurring_total.toLocaleString()}`}
              color="text-red-400"
            />
            <StatCard
              label="Disposable income"
              value={`£${summary.disposable_income.toLocaleString()}`}
              sub="salary − recurring"
              color={summary.disposable_income >= 0 ? "text-emerald-400" : "text-red-500"}
            />
            <StatCard
              label="Total spent"
              value={`£${summary.total_out.toLocaleString()}`}
              sub={`${summary.transaction_count} transactions`}
            />
          </div>

          {/* Category pie */}
          {summary.category_breakdown.length > 0 && (
            <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
              <h2 className="text-sm font-medium text-gray-300 mb-4">Spending by category</h2>
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={summary.category_breakdown}
                    dataKey="amount"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    label={({ name, percent }) =>
                      `${name} ${(percent * 100).toFixed(0)}%`
                    }
                    labelLine={false}
                  >
                    {summary.category_breakdown.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => `£${v.toLocaleString()}`} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}

      {/* 6-month trend */}
      {trend.length > 0 && (
        <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
          <h2 className="text-sm font-medium text-gray-300 mb-4">6-month trend</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={trendData}>
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#9ca3af" }} />
              <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} />
              <Tooltip formatter={(v: number) => `£${v.toLocaleString()}`} />
              <Legend />
              <Bar dataKey="In" fill="#22c55e" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Out" fill="#ef4444" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Disposable" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

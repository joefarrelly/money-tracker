import { useEffect, useState } from "react";
import { getMonthlySummary, getTrend, getRecentTransactions } from "../api/client";
import type { MonthlySummary, Transaction, RecurringActual, PayslipLineItem } from "../types";

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

const fmt = (v: number) =>
  "£" + Math.abs(v).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function prevMonthOf(year: number, month: number) {
  return month === 1 ? { year: year - 1, month: 12 } : { year, month: month - 1 };
}

// ── Stat card ──────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  color = "text-white",
  sub,
  delta,
  positiveIsGood = true,
}: {
  label: string;
  value: string;
  color?: string;
  sub?: string;
  delta?: number | null;
  positiveIsGood?: boolean;
}) {
  let deltaEl: React.ReactNode = null;
  if (delta != null && delta !== 0) {
    const good = positiveIsGood ? delta > 0 : delta < 0;
    const arrow = delta > 0 ? "↑" : "↓";
    deltaEl = (
      <span className={`text-xs font-medium ${good ? "text-emerald-400" : "text-red-400"}`}>
        {arrow} {fmt(delta)}
      </span>
    );
  }

  return (
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
      <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
      <div className="flex items-center gap-2 mt-1">
        {sub && <p className="text-xs text-gray-500">{sub}</p>}
        {deltaEl}
      </div>
    </div>
  );
}

// ── Category horizontal bars ───────────────────────────────────────────────────

function CategoryBars({ breakdown }: { breakdown: MonthlySummary["category_breakdown"] }) {
  if (breakdown.length === 0) {
    return (
      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800 flex items-center justify-center h-full">
        <p className="text-gray-500 text-sm">No spending data</p>
      </div>
    );
  }

  const max = breakdown[0].amount;

  return (
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
      <h2 className="text-sm font-medium text-gray-300 mb-4">Spending by category</h2>
      <div className="space-y-3">
        {breakdown.slice(0, 8).map((cat) => (
          <div key={cat.name}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-300 truncate max-w-[60%]">{cat.name}</span>
              <span className="text-gray-400">
                {fmt(cat.amount)}
                <span className="text-gray-600 ml-1">({cat.count})</span>
              </span>
            </div>
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${(cat.amount / max) * 100}%`,
                  backgroundColor: cat.color,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Payslip breakdown ──────────────────────────────────────────────────────────

function PayslipBreakdown({ salaryEntries }: { salaryEntries: MonthlySummary["salary_entries"] }) {
  if (salaryEntries.length === 0) {
    return (
      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800 flex items-center justify-center h-full">
        <p className="text-gray-500 text-sm">No payslip this month</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-800 space-y-5">
      <h2 className="text-sm font-medium text-gray-300">Payslip breakdown</h2>
      {salaryEntries.map((s) => {
        const earnings = s.line_items.filter((li) => li.line_type === "earning");
        const deductions = s.line_items.filter((li) => li.line_type === "deduction");
        const hasItems = s.line_items.length > 0;

        return (
          <div key={s.id}>
            {salaryEntries.length > 1 && (
              <p className="text-xs text-gray-500 mb-2">{s.employer ?? "Employer"}</p>
            )}

            {hasItems ? (
              <div className="space-y-1 text-sm">
                {/* Gross */}
                {earnings.length > 0 && (
                  <div className="flex justify-between text-gray-300">
                    <span>Gross pay</span>
                    <span className="text-green-400 font-medium">
                      {fmt(earnings.reduce((a, li) => a + li.amount, 0))}
                    </span>
                  </div>
                )}

                {/* Deductions */}
                {deductions.length > 0 && (
                  <div className="mt-2 space-y-1">
                    <p className="text-xs text-gray-500 uppercase tracking-wide">Deductions</p>
                    {deductions.map((li, i) => (
                      <DeductionRow key={i} li={li} />
                    ))}
                  </div>
                )}

                {/* Divider + net */}
                <div className="border-t border-gray-700 mt-2 pt-2 flex justify-between font-semibold">
                  <span className="text-gray-200">Net pay</span>
                  <span className="text-emerald-400">{fmt(s.net_amount)}</span>
                </div>
              </div>
            ) : (
              /* Manual entry — no line items */
              <div className="space-y-1 text-sm">
                {s.gross_amount != null && (
                  <div className="flex justify-between text-gray-300">
                    <span>Gross</span>
                    <span>{fmt(s.gross_amount)}</span>
                  </div>
                )}
                <div className="flex justify-between font-semibold">
                  <span className="text-gray-200">Net pay</span>
                  <span className="text-emerald-400">{fmt(s.net_amount)}</span>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function DeductionRow({ li }: { li: PayslipLineItem }) {
  return (
    <div className="flex justify-between text-gray-400">
      <span className="truncate max-w-[65%]">{li.description}</span>
      <span className="text-red-400">−{fmt(li.amount)}</span>
    </div>
  );
}

// ── Spending vs salary progress ────────────────────────────────────────────────

function SpendingProgress({
  spent,
  salary,
  recurring,
}: {
  spent: number;
  salary: number;
  recurring: number;
}) {
  if (salary <= 0) return null;

  const spentPct = Math.min((spent / salary) * 100, 100);
  const recurringPct = Math.min((recurring / salary) * 100, 100);
  const nonRecurringPct = Math.max(spentPct - recurringPct, 0);
  const remaining = salary - spent;

  const barColor =
    spentPct >= 100 ? "bg-red-500" : spentPct >= 85 ? "bg-amber-500" : "bg-emerald-500";

  return (
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
      <div className="flex justify-between items-baseline mb-3">
        <h2 className="text-sm font-medium text-gray-300">Spending vs salary</h2>
        <span className={`text-sm font-semibold ${remaining >= 0 ? "text-emerald-400" : "text-red-400"}`}>
          {remaining >= 0 ? `${fmt(remaining)} remaining` : `${fmt(remaining)} over`}
        </span>
      </div>

      {/* Stacked bar */}
      <div className="h-3 bg-gray-800 rounded-full overflow-hidden flex">
        <div
          className="h-full bg-red-700 transition-all duration-500"
          style={{ width: `${recurringPct}%` }}
          title={`Recurring: ${fmt(recurring)}`}
        />
        <div
          className={`h-full ${barColor} transition-all duration-500`}
          style={{ width: `${nonRecurringPct}%` }}
          title={`Other spending: ${fmt(Math.max(spent - recurring, 0))}`}
        />
      </div>

      <div className="flex justify-between text-xs text-gray-500 mt-2">
        <div className="flex gap-4">
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-sm bg-red-700" />
            Recurring {fmt(recurring)}
          </span>
          <span className="flex items-center gap-1">
            <span className={`inline-block w-2 h-2 rounded-sm ${barColor}`} />
            Other {fmt(Math.max(spent - recurring, 0))}
          </span>
        </div>
        <span>of {fmt(salary)}</span>
      </div>
    </div>
  );
}

// ── Recent transactions ────────────────────────────────────────────────────────

function RecentTransactions({ transactions }: { transactions: Transaction[] }) {
  return (
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
      <h2 className="text-sm font-medium text-gray-300 mb-3">Recent transactions</h2>
      {transactions.length === 0 ? (
        <p className="text-gray-500 text-sm">No transactions this month</p>
      ) : (
        <div className="space-y-2">
          {transactions.map((t) => (
            <div key={t.id} className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 min-w-0">
                {t.category && (
                  <span
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ backgroundColor: t.category.color }}
                  />
                )}
                <div className="min-w-0">
                  <p className="text-sm text-gray-200 truncate">{t.description}</p>
                  <p className="text-xs text-gray-500">{t.date}</p>
                </div>
              </div>
              <span
                className={`text-sm font-medium flex-shrink-0 ${
                  t.amount >= 0 ? "text-green-400" : "text-gray-300"
                }`}
              >
                {t.amount >= 0 ? "+" : "−"}
                {fmt(t.amount)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Recurring status ───────────────────────────────────────────────────────────

function RecurringStatus({ actuals }: { actuals: RecurringActual[] }) {
  if (actuals.length === 0) {
    return (
      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
        <h2 className="text-sm font-medium text-gray-300 mb-3">Recurring expenses</h2>
        <p className="text-gray-500 text-sm">No recurring expenses tracked</p>
      </div>
    );
  }

  const found = actuals.filter((a) => a.found_this_month);
  const missing = actuals.filter((a) => !a.found_this_month);
  const over = actuals.filter((a) => a.is_over);

  return (
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium text-gray-300">Recurring this month</h2>
        <div className="flex gap-2 text-xs">
          <span className="text-emerald-400">{found.length} seen</span>
          {over.length > 0 && <span className="text-amber-400">{over.length} over</span>}
          {missing.length > 0 && <span className="text-gray-500">{missing.length} pending</span>}
        </div>
      </div>

      <div className="space-y-2 max-h-72 overflow-y-auto">
        {/* Over budget first */}
        {over.map((a) => (
          <RecurringRow key={a.id} a={a} />
        ))}
        {/* Found, not over */}
        {found.filter((a) => !a.is_over).map((a) => (
          <RecurringRow key={a.id} a={a} />
        ))}
        {/* Not found yet */}
        {missing.map((a) => (
          <RecurringRow key={a.id} a={a} />
        ))}
      </div>
    </div>
  );
}

function RecurringRow({ a }: { a: RecurringActual }) {
  let statusDot = "bg-gray-600";
  let amountEl: React.ReactNode;

  if (!a.found_this_month) {
    statusDot = "bg-gray-600";
    amountEl = (
      <span className="text-xs text-gray-500">pending {fmt(a.monthly_cost)}</span>
    );
  } else if (a.is_over) {
    statusDot = "bg-amber-400";
    amountEl = (
      <span className="text-xs text-amber-400 font-medium">
        {fmt(a.actual_amount)}
        <span className="text-gray-500 ml-1">/ {fmt(a.monthly_cost)}</span>
      </span>
    );
  } else {
    statusDot = "bg-emerald-500";
    amountEl = (
      <span className="text-xs text-gray-300">{fmt(a.actual_amount)}</span>
    );
  }

  return (
    <div className="flex items-center justify-between gap-2">
      <div className="flex items-center gap-2 min-w-0">
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${statusDot}`} />
        <span className="text-sm text-gray-300 truncate">{a.merchant_pattern}</span>
        {a.frequency === "annual" && (
          <span className="text-xs text-gray-600">/yr</span>
        )}
      </div>
      {amountEl}
    </div>
  );
}

// ── Trend table ────────────────────────────────────────────────────────────────

function TrendTable({ trend }: { trend: MonthlySummary[] }) {
  if (trend.length === 0) return null;

  return (
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
      <h2 className="text-sm font-medium text-gray-300 mb-4">6-month summary</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-gray-500 uppercase tracking-wide border-b border-gray-800">
              <th className="text-left pb-2">Month</th>
              <th className="text-right pb-2">Salary</th>
              <th className="text-right pb-2">Spent</th>
              <th className="text-right pb-2">Net</th>
              <th className="text-right pb-2">Savings rate</th>
            </tr>
          </thead>
          <tbody>
            {trend.map((m) => {
              const rate =
                m.salary > 0
                  ? Math.round(((m.salary - m.total_out) / m.salary) * 100)
                  : null;
              return (
                <tr key={`${m.year}-${m.month}`} className="border-b border-gray-800/50 last:border-0">
                  <td className="py-2.5 text-gray-300">
                    {MONTHS[m.month - 1]} {m.year}
                  </td>
                  <td className="py-2.5 text-right text-green-400">{fmt(m.salary)}</td>
                  <td className="py-2.5 text-right text-red-400">{fmt(m.total_out)}</td>
                  <td className={`py-2.5 text-right font-medium ${m.net >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                    {m.net >= 0 ? "+" : "−"}{fmt(m.net)}
                  </td>
                  <td className="py-2.5 text-right">
                    {rate != null ? (
                      <span
                        className={
                          rate >= 20
                            ? "text-emerald-400"
                            : rate >= 0
                            ? "text-amber-400"
                            : "text-red-400"
                        }
                      >
                        {rate}%
                      </span>
                    ) : (
                      <span className="text-gray-600">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Main Dashboard ─────────────────────────────────────────────────────────────

export default function Dashboard() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [summary, setSummary] = useState<MonthlySummary | null>(null);
  const [prevSummary, setPrevSummary] = useState<MonthlySummary | null>(null);
  const [trend, setTrend] = useState<MonthlySummary[]>([]);
  const [recentTxns, setRecentTxns] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const prev = prevMonthOf(year, month);
    Promise.all([
      getMonthlySummary(year, month),
      getMonthlySummary(prev.year, prev.month),
      getTrend(6),
      getRecentTransactions(year, month, 8),
    ])
      .then(([s, ps, t, rt]) => {
        setSummary(s);
        setPrevSummary(ps);
        setTrend(t);
        setRecentTxns(rt.transactions);
      })
      .finally(() => setLoading(false));
  }, [year, month]);

  function navigate(dir: -1 | 1) {
    if (dir === -1) {
      const p = prevMonthOf(year, month);
      setYear(p.year);
      setMonth(p.month);
    } else {
      const next = month === 12 ? { year: year + 1, month: 1 } : { year, month: month + 1 };
      setYear(next.year);
      setMonth(next.month);
    }
  }

  const delta = (cur: number, prev: number) => (prevSummary ? cur - prev : null);

  const savingsRate =
    summary && summary.salary > 0
      ? Math.round(((summary.salary - summary.total_out) / summary.salary) * 100)
      : null;

  const prevSavingsRate =
    prevSummary && prevSummary.salary > 0
      ? Math.round(((prevSummary.salary - prevSummary.total_out) / prevSummary.salary) * 100)
      : null;

  return (
    <div className="space-y-5">
      {/* Month navigator */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg px-3 py-1.5 text-sm"
        >
          ←
        </button>
        <div className="flex items-center gap-2">
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
        <button
          onClick={() => navigate(1)}
          className="bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg px-3 py-1.5 text-sm"
        >
          →
        </button>
      </div>

      {loading && <p className="text-gray-400 py-8 text-center">Loading…</p>}

      {!loading && summary && (
        <>
          {/* ── Stat cards ── */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              label="Net salary"
              value={fmt(summary.salary)}
              color="text-green-400"
              delta={delta(summary.salary, prevSummary?.salary ?? 0)}
              positiveIsGood={true}
            />
            <StatCard
              label="Total spent"
              value={fmt(summary.total_out)}
              color="text-red-400"
              sub={`${summary.transaction_count} txns`}
              delta={delta(summary.total_out, prevSummary?.total_out ?? 0)}
              positiveIsGood={false}
            />
            <StatCard
              label="Net cash flow"
              value={fmt(summary.net)}
              color={summary.net >= 0 ? "text-emerald-400" : "text-red-500"}
              sub="money in − out"
              delta={delta(summary.net, prevSummary?.net ?? 0)}
              positiveIsGood={true}
            />
            <StatCard
              label="Savings rate"
              value={savingsRate != null ? `${savingsRate}%` : "—"}
              color={
                savingsRate == null
                  ? "text-gray-400"
                  : savingsRate >= 20
                  ? "text-emerald-400"
                  : savingsRate >= 0
                  ? "text-amber-400"
                  : "text-red-500"
              }
              sub="of salary unspent"
              delta={
                savingsRate != null && prevSavingsRate != null
                  ? savingsRate - prevSavingsRate
                  : null
              }
              positiveIsGood={true}
            />
          </div>

          {/* ── Category bars + Payslip breakdown ── */}
          <div className="grid md:grid-cols-5 gap-5">
            <div className="md:col-span-3">
              <CategoryBars breakdown={summary.category_breakdown} />
            </div>
            <div className="md:col-span-2">
              <PayslipBreakdown salaryEntries={summary.salary_entries} />
            </div>
          </div>

          {/* ── Spending vs salary ── */}
          <SpendingProgress
            spent={summary.total_out}
            salary={summary.salary}
            recurring={summary.recurring_total}
          />

          {/* ── Recent transactions + Recurring status ── */}
          <div className="grid md:grid-cols-2 gap-5">
            <RecentTransactions transactions={recentTxns} />
            <RecurringStatus actuals={summary.recurring_actuals} />
          </div>
        </>
      )}

      {/* ── 6-month summary ── */}
      {!loading && <TrendTable trend={trend} />}
    </div>
  );
}

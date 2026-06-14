import { useEffect, useState } from "react";
import { Spinner } from "../components/Spinner";
import { useAuth } from "../auth";
import {
  getEmailImports,
  pollEmails,
  confirmEmailImport,
  skipEmailImport,
  deleteEmailImport,
  getEmailConfig,
  setEmailConfig,
  deleteEmailConfig,
  type EmailConfig,
} from "../api/client";
import type { EmailImport } from "../types";

const fmt = (v: number) =>
  "£" +
  v.toLocaleString("en-GB", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

function statusBadge(status: EmailImport["status"]) {
  const map: Record<string, string> = {
    pending: "bg-yellow-900/40 text-yellow-300",
    imported: "bg-emerald-900/40 text-emerald-300",
    skipped: "bg-slate-800 text-slate-400",
    failed: "bg-red-900/40 text-red-300",
  };
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded-full ${map[status] ?? map.skipped}`}
    >
      {status}
    </span>
  );
}

type LineItem = {
  description: string;
  rate: number | null;
  units: string | null;
  amount: number;
  this_year_amount: number | null;
  line_type: "earning" | "deduction";
};

function PayslipDetail({ d }: { d: Record<string, unknown> }) {
  const items = (d.line_items ?? []) as LineItem[];
  const earnings = items.filter((i) => i.line_type === "earning");
  const deductions = items.filter((i) => i.line_type === "deduction");

  const Section = ({
    title,
    rows,
    colorClass,
  }: {
    title: string;
    rows: LineItem[];
    colorClass: string;
  }) => (
    <>
      <tr className="bg-slate-800/60">
        <td
          colSpan={3}
          className={`px-3 py-1 text-xs font-semibold uppercase tracking-wider ${colorClass}`}
        >
          {title}
        </td>
      </tr>
      {rows.map((item, i) => (
        <tr key={i} className="border-t border-slate-800/30">
          <td className="px-3 py-1.5 text-sm text-slate-300 pl-5">
            {item.description}
          </td>
          <td className="px-3 py-1.5 text-xs text-slate-500 text-right">
            {item.rate != null ? fmt(item.rate) : ""}
            {item.units ? (
              <span className="ml-1 text-slate-600">× {item.units}</span>
            ) : null}
          </td>
          <td
            className={`px-3 py-1.5 text-sm text-right font-medium ${colorClass}`}
          >
            {fmt(item.amount)}
          </td>
        </tr>
      ))}
    </>
  );

  return (
    <div>
      <div className="flex gap-6 mb-3 text-sm">
        <span>
          Net pay{" "}
          <span className="text-emerald-400 font-semibold">
            {fmt(d.net_pay as number)}
          </span>
        </span>
        {d.gross_pay != null && (
          <span>
            Gross{" "}
            <span className="text-slate-300 font-medium">
              {fmt(d.gross_pay as number)}
            </span>
          </span>
        )}
        {d.employer != null && (
          <span className="text-slate-400">{String(d.employer)}</span>
        )}
      </div>
      {items.length > 0 && (
        <div className="rounded-lg overflow-hidden border border-slate-800">
          <table className="w-full text-sm bg-slate-950/60">
            <thead>
              <tr className="text-xs text-slate-500 border-b border-slate-800">
                <th className="px-3 py-2 text-left pl-5">Description</th>
                <th className="px-3 py-2 text-right">Rate / Units</th>
                <th className="px-3 py-2 text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {earnings.length > 0 && (
                <Section
                  title="Earnings"
                  rows={earnings}
                  colorClass="text-green-400"
                />
              )}
              {deductions.length > 0 && (
                <Section
                  title="Deductions"
                  rows={deductions}
                  colorClass="text-red-400"
                />
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

type TxnRow = { date: string; description: string; amount: number };

function BankDetail({ d }: { d: Record<string, unknown> }) {
  const txns = ((d.transactions ?? []) as TxnRow[]).slice(0, 10);
  const total = d.transaction_count as number;

  return (
    <div>
      <div className="flex gap-6 mb-3 text-sm">
        <span>
          <span className="text-sky-400 font-semibold">
            {total} transactions
          </span>
        </span>
        {d.format_name != null && (
          <span className="text-slate-400">{String(d.format_name)}</span>
        )}
        {d.account_number != null && d.account_number !== "unknown" && (
          <span className="text-slate-400">
            Account ending {String(d.account_number).slice(-4)}
          </span>
        )}
      </div>
      {txns.length > 0 && (
        <div className="rounded-lg overflow-hidden border border-slate-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-slate-500 border-b border-slate-800 bg-slate-950/60">
                <th className="px-3 py-2 text-left">Date</th>
                <th className="px-3 py-2 text-left">Description</th>
                <th className="px-3 py-2 text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {txns.map((t, i) => (
                <tr key={i} className="border-t border-slate-800/40">
                  <td className="px-3 py-1.5 text-xs text-slate-400 tabular-nums whitespace-nowrap">
                    {t.date}
                  </td>
                  <td className="px-3 py-1.5 text-sm text-slate-300 truncate max-w-[260px]">
                    {t.description}
                  </td>
                  <td
                    className={`px-3 py-1.5 text-sm text-right font-medium tabular-nums ${
                      t.amount >= 0 ? "text-emerald-400" : "text-red-400"
                    }`}
                  >
                    {t.amount >= 0 ? "+" : ""}
                    {fmt(t.amount)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {total > 10 && (
            <p className="px-3 py-2 text-xs text-slate-500 border-t border-slate-800 bg-slate-950/60">
              +{total - 10} more transactions
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function ImportCard({
  record,
  expanded,
  onToggle,
  onConfirm,
  onSkip,
  onDismiss,
  busy,
}: {
  record: EmailImport;
  expanded: boolean;
  onToggle: () => void;
  onConfirm: () => void;
  onSkip: () => void;
  onDismiss: () => void;
  busy: boolean;
}) {
  const d = record.raw_data;
  const isPending = record.status === "pending";

  const receivedLabel = record.received_at
    ? new Date(record.received_at).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : null;

  return (
    <div
      className={`bg-slate-900 border rounded-xl overflow-hidden transition-colors ${
        expanded
          ? "border-indigo-600/40"
          : "border-slate-800 hover:border-slate-700"
      }`}
    >
      <div className="px-4 py-3 flex items-center gap-3">
        <button
          className="flex items-center gap-3 flex-1 min-w-0 text-left"
          onClick={onToggle}
        >
          <div
            className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-sm ${
              record.import_type === "payslip"
                ? "bg-emerald-900/40 text-emerald-400"
                : "bg-sky-900/40 text-sky-400"
            }`}
          >
            {record.import_type === "payslip" ? "💰" : "🏦"}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium text-slate-200 truncate">
                {record.subject ?? record.filename ?? "Untitled"}
              </span>
              {statusBadge(record.status)}
            </div>
            <p className="text-xs text-slate-500 mt-0.5 truncate">
              {record.filename && (
                <span className="text-slate-400 mr-2">{record.filename}</span>
              )}
              {record.sender && <span>{record.sender}</span>}
              {receivedLabel && <span> · {receivedLabel}</span>}
            </p>
          </div>
        </button>

        <div className="flex items-center gap-2 flex-shrink-0">
          {isPending && (
            <button
              onClick={onSkip}
              disabled={busy}
              title="Skip"
              className="text-xs text-slate-500 hover:text-slate-300 disabled:opacity-40 transition-colors px-2 py-1 rounded hover:bg-slate-800"
            >
              Skip
            </button>
          )}
          {!isPending && (
            <button
              onClick={onDismiss}
              disabled={busy}
              title="Dismiss"
              className="text-xs text-slate-600 hover:text-red-400 disabled:opacity-40 transition-colors px-2 py-1 rounded hover:bg-slate-800"
            >
              Dismiss
            </button>
          )}
          <svg
            className={`w-4 h-4 text-slate-500 transition-transform cursor-pointer ${
              expanded ? "rotate-180" : ""
            }`}
            onClick={onToggle}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-slate-800 px-4 py-4 space-y-4">
          {d && record.import_type === "payslip" && <PayslipDetail d={d} />}
          {d && record.import_type === "bank_statement" && <BankDetail d={d} />}

          {record.error_message && (
            <p className="text-sm text-red-400 bg-red-900/20 border border-red-800/30 rounded-lg px-3 py-2">
              {record.error_message}
            </p>
          )}

          {record.imported_at && (
            <p className="text-xs text-slate-500">
              Imported{" "}
              {new Date(record.imported_at).toLocaleDateString("en-GB")}
            </p>
          )}

          <div className="flex items-center justify-end gap-3 pt-1">
            {isPending && (
              <>
                <button
                  onClick={onSkip}
                  disabled={busy}
                  className="text-sm text-slate-400 hover:text-slate-200 transition-colors disabled:opacity-40"
                >
                  Skip
                </button>
                <button
                  onClick={onConfirm}
                  disabled={busy}
                  className="text-sm bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 px-4 py-1.5 rounded-lg font-medium transition-colors"
                >
                  Import
                </button>
              </>
            )}
            {!isPending && (
              <button
                onClick={onDismiss}
                disabled={busy}
                className="text-xs text-slate-600 hover:text-red-400 transition-colors disabled:opacity-40"
              >
                Dismiss
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function EmailConfigForm({
  userEmail,
  existing,
  onSaved,
  onCancel,
}: {
  userEmail: string | null;
  existing: EmailConfig | null;
  onSaved: (cfg: EmailConfig) => void;
  onCancel?: () => void;
}) {
  const [password, setPassword] = useState("");
  const [label, setLabel] = useState(existing?.label ?? "INBOX");
  const [enabled, setEnabled] = useState(existing?.enabled ?? true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) {
      setError("App Password is required");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const cfg = await setEmailConfig({
        app_password: password.trim(),
        label: label.trim() || "INBOX",
        enabled,
      });
      onSaved(cfg);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSave} className="space-y-4">
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <div>
          <p className="text-sm text-slate-300 font-medium mb-1">
            Gmail account
          </p>
          <p className="text-sm text-slate-400">
            {userEmail ?? "your Google account email"}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Email polling uses this account — the same one you sign in with.
          </p>
        </div>

        <div>
          <label className="block text-sm text-slate-300 font-medium mb-1.5">
            Gmail App Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="xxxx xxxx xxxx xxxx"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
          <p className="text-xs text-slate-500 mt-1.5">
            Generate one at{" "}
            <span className="text-slate-400">
              Google Account → Security → 2-Step Verification → App passwords
            </span>
            . Select app: Mail, device: Other.
          </p>
        </div>

        <div>
          <label className="block text-sm text-slate-300 font-medium mb-1.5">
            Gmail label{" "}
            <span className="text-slate-500 font-normal">(optional)</span>
          </label>
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="INBOX"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
          <p className="text-xs text-slate-500 mt-1.5">
            Only check a specific label (e.g.{" "}
            <span className="text-slate-400">finance</span>). Leave as INBOX to
            check all mail.
          </p>
        </div>

        {existing && (
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="w-4 h-4 rounded"
            />
            <span className="text-sm text-slate-300">
              Enable automatic polling
            </span>
          </label>
        )}

        {error && (
          <p className="text-sm text-red-400 bg-red-900/20 border border-red-800/30 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <div className="flex items-center gap-3 pt-1">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="text-sm text-slate-400 hover:text-slate-200 transition-colors"
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            disabled={saving}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            {saving ? "Saving…" : existing ? "Update" : "Save & enable"}
          </button>
        </div>
      </div>
    </form>
  );
}

export default function EmailImports() {
  const { email: userEmail } = useAuth();
  const [config, setConfig] = useState<EmailConfig | null>(null);
  const [configLoading, setConfigLoading] = useState(true);
  const [showConfigForm, setShowConfigForm] = useState(false);
  const [removingConfig, setRemovingConfig] = useState(false);

  const [imports, setImports] = useState<EmailImport[]>([]);
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(false);
  const [pollMsg, setPollMsg] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const loadConfig = () =>
    getEmailConfig()
      .then(setConfig)
      .catch(() => null)
      .finally(() => setConfigLoading(false));

  const loadImports = () =>
    getEmailImports()
      .then(setImports)
      .catch((e) => setError(e.message));

  useEffect(() => {
    loadConfig();
    setLoading(true);
    loadImports().finally(() => setLoading(false));
  }, []);

  const handlePoll = async () => {
    setPolling(true);
    setPollMsg(null);
    setError(null);
    try {
      const res = await pollEmails();
      setPollMsg(res.message);
      await loadImports();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Poll failed");
    } finally {
      setPolling(false);
    }
  };

  const handleRemoveConfig = async () => {
    setRemovingConfig(true);
    try {
      await deleteEmailConfig();
      setConfig({ configured: false, label: "INBOX", enabled: true });
      setShowConfigForm(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to remove config");
    } finally {
      setRemovingConfig(false);
    }
  };

  const withBusy = async (id: number, fn: () => Promise<unknown>) => {
    setBusyId(id);
    setError(null);
    try {
      await fn();
      await loadImports();
      setExpandedId(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  };

  if (configLoading) return <Spinner />;

  // Setup screen — no config yet
  if (!config?.configured && !showConfigForm) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-lg font-semibold">Email Imports</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Automatically import bank statements and payslips sent to your Gmail
            inbox.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl px-6 py-8 text-center space-y-4">
          <div className="w-12 h-12 bg-slate-800 rounded-xl flex items-center justify-center text-2xl mx-auto">
            ✉️
          </div>
          <div>
            <p className="text-slate-200 font-medium">Connect your Gmail</p>
            <p className="text-sm text-slate-400 mt-1 max-w-sm mx-auto">
              Add a Gmail App Password to let Money Tracker poll your inbox for
              PDFs with "payslip" or "bank" in the subject.
            </p>
          </div>
          <button
            onClick={() => setShowConfigForm(true)}
            className="bg-indigo-600 hover:bg-indigo-500 px-5 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Set up email polling
          </button>
        </div>
      </div>
    );
  }

  if (!config?.configured && showConfigForm) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-lg font-semibold">Email Imports</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Connect your Gmail to enable automatic PDF imports.
          </p>
        </div>
        <EmailConfigForm
          userEmail={userEmail}
          existing={null}
          onSaved={(cfg) => {
            setConfig(cfg);
            setShowConfigForm(false);
          }}
          onCancel={() => setShowConfigForm(false)}
        />
      </div>
    );
  }

  const pending = imports.filter((i) => i.status === "pending");
  const history = imports.filter((i) => i.status !== "pending");

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold">Email Imports</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Send PDFs to{" "}
            <span className="text-slate-300">
              {config?.user_email ?? userEmail}
            </span>{" "}
            with "payslip" or "bank" in the subject — they'll appear here for
            review.
          </p>
        </div>
        <button
          onClick={handlePoll}
          disabled={polling}
          className="flex-shrink-0 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          {polling ? "Checking…" : "Check now"}
        </button>
      </div>

      {pollMsg && (
        <p className="text-sm text-emerald-400 bg-emerald-900/20 border border-emerald-800/40 rounded-lg px-4 py-2">
          {pollMsg}
        </p>
      )}
      {error && (
        <p className="text-sm text-red-400 bg-red-900/20 border border-red-800/40 rounded-lg px-4 py-2">
          {error}
        </p>
      )}

      {loading && <Spinner />}

      {!loading && (
        <>
          <section>
            <h2 className="text-sm font-medium text-slate-300 mb-3">
              Pending
              {pending.length > 0 && (
                <span className="ml-2 text-xs text-yellow-400 bg-yellow-900/30 px-2 py-0.5 rounded-full">
                  {pending.length}
                </span>
              )}
            </h2>
            {pending.length === 0 ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-8 text-center text-sm text-slate-500">
                No pending imports. Send a PDF to your inbox with "payslip" or
                "bank" in the subject and click "Check now".
              </div>
            ) : (
              <div className="space-y-2">
                {pending.map((r) => (
                  <ImportCard
                    key={r.id}
                    record={r}
                    expanded={expandedId === r.id}
                    onToggle={() =>
                      setExpandedId(expandedId === r.id ? null : r.id)
                    }
                    busy={busyId === r.id}
                    onConfirm={() =>
                      withBusy(r.id, () => confirmEmailImport(r.id))
                    }
                    onSkip={() => withBusy(r.id, () => skipEmailImport(r.id))}
                    onDismiss={() =>
                      withBusy(r.id, () => deleteEmailImport(r.id))
                    }
                  />
                ))}
              </div>
            )}
          </section>

          {history.length > 0 && (
            <section>
              <h2 className="text-sm font-medium text-slate-300 mb-3">
                History
                <span className="ml-2 text-xs text-slate-500">
                  ({history.length})
                </span>
              </h2>
              <div className="space-y-2">
                {history.map((r) => (
                  <ImportCard
                    key={r.id}
                    record={r}
                    expanded={expandedId === r.id}
                    onToggle={() =>
                      setExpandedId(expandedId === r.id ? null : r.id)
                    }
                    busy={busyId === r.id}
                    onConfirm={() =>
                      withBusy(r.id, () => confirmEmailImport(r.id))
                    }
                    onSkip={() => withBusy(r.id, () => skipEmailImport(r.id))}
                    onDismiss={() =>
                      withBusy(r.id, () => deleteEmailImport(r.id))
                    }
                  />
                ))}
              </div>
            </section>
          )}
        </>
      )}

      {/* Email settings panel */}
      <section>
        <button
          onClick={() => setShowConfigForm((v) => !v)}
          className="text-sm text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1"
        >
          <svg
            className={`w-3.5 h-3.5 transition-transform ${showConfigForm ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
          Email settings
        </button>

        {showConfigForm && (
          <div className="mt-3 space-y-3">
            <EmailConfigForm
              userEmail={userEmail}
              existing={config}
              onSaved={(cfg) => {
                setConfig(cfg);
                setShowConfigForm(false);
              }}
              onCancel={() => setShowConfigForm(false)}
            />
            <button
              onClick={handleRemoveConfig}
              disabled={removingConfig}
              className="text-xs text-red-500 hover:text-red-400 disabled:opacity-40 transition-colors"
            >
              {removingConfig ? "Removing…" : "Remove email config"}
            </button>
          </div>
        )}
      </section>
    </div>
  );
}

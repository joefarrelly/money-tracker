import { useEffect, useRef, useState } from "react";
import { bulkUpload, confirmUpload, getFormats, previewUpload } from "../api/client";
import type { BulkFileResult, BulkUploadResult, ColumnMapping, ColumnRole, PreviewResponse, StatementFormat, Transaction } from "../types";

// ── Role metadata ─────────────────────────────────────────────────────────────

const ROLES: { value: ColumnRole; label: string; color: string }[] = [
  { value: "date",             label: "Date",                  color: "text-blue-400" },
  { value: "description",      label: "Description",           color: "text-purple-400" },
  { value: "date_description", label: "Date + Description",    color: "text-cyan-400" },
  { value: "money_in",         label: "Money In",              color: "text-green-400" },
  { value: "money_out",        label: "Money Out",             color: "text-red-400" },
  { value: "amount",           label: "Amount (±)",            color: "text-yellow-400" },
  { value: "balance",          label: "Balance",               color: "text-gray-400" },
  { value: "ignore",           label: "Ignore",                color: "text-gray-600" },
];

function roleColor(role: string) {
  return ROLES.find((r) => r.value === role)?.color ?? "text-gray-400";
}

function roleLabel(role: string) {
  return ROLES.find((r) => r.value === role)?.label ?? role;
}

// ── Mapping helpers ───────────────────────────────────────────────────────────

/** Convert { colIndex: role } assignment map to the API ColumnMapping shape. */
function buildColumnMapping(
  roleMap: Record<number, ColumnRole>,
  preview: PreviewResponse
): ColumnMapping {
  const first = (role: ColumnRole) => {
    const entry = Object.entries(roleMap).find(([, r]) => r === role);
    return entry != null ? Number(entry[0]) : null;
  };

  const hasIn  = first("money_in")  != null;
  const hasOut = first("money_out") != null;
  const amount_style: "split" | "signed" = hasIn || hasOut ? "split" : "signed";

  return {
    date_col:             first("date"),
    description_col:      first("description"),
    date_description_col: first("date_description"),
    balance_col:          first("balance"),
    amount_style,
    amount_col:    amount_style === "signed" ? first("amount") : null,
    money_in_col:  amount_style === "split"  ? first("money_in")  : null,
    money_out_col: amount_style === "split"  ? first("money_out") : null,
    date_format:  preview.proposed_mapping.date_format,
    year_source:  preview.proposed_mapping.year_source,
  };
}

/** Initialise roleMap from a ColumnMapping object. */
function mappingToRoleMap(m: ColumnMapping): Record<number, ColumnRole> {
  const out: Record<number, ColumnRole> = {};
  if (m.date_col             != null) out[m.date_col]             = "date";
  if (m.description_col      != null) out[m.description_col]      = "description";
  if (m.date_description_col != null) out[m.date_description_col] = "date_description";
  if (m.balance_col          != null) out[m.balance_col]          = "balance";
  if (m.amount_col           != null) out[m.amount_col]           = "amount";
  if (m.money_in_col         != null) out[m.money_in_col]         = "money_in";
  if (m.money_out_col        != null) out[m.money_out_col]        = "money_out";
  return out;
}

function validateRoleMap(roleMap: Record<number, ColumnRole>): string | null {
  const roles = Object.values(roleMap);
  const hasMerged = roles.includes("date_description");
  if (!hasMerged && !roles.includes("date"))        return "Assign a Date column (or Date + Description)";
  if (!hasMerged && !roles.includes("description")) return "Assign a Description column (or Date + Description)";
  const hasAmount = roles.includes("amount");
  const hasIn     = roles.includes("money_in");
  const hasOut    = roles.includes("money_out");
  if (!hasAmount && !hasIn && !hasOut) return "Assign at least one amount column";
  return null;
}

function formatToRoleMap(fmt: StatementFormat): Record<number, ColumnRole> {
  const out: Record<number, ColumnRole> = {};
  if (fmt.date_col             != null) out[fmt.date_col]             = "date";
  if (fmt.description_col      != null) out[fmt.description_col]      = "description";
  if (fmt.date_description_col != null) out[fmt.date_description_col] = "date_description";
  if (fmt.balance_col          != null) out[fmt.balance_col]          = "balance";
  if (fmt.amount_col           != null) out[fmt.amount_col]           = "amount";
  if (fmt.money_in_col         != null) out[fmt.money_in_col]         = "money_in";
  if (fmt.money_out_col        != null) out[fmt.money_out_col]        = "money_out";
  return out;
}

// ── Bulk upload component ─────────────────────────────────────────────────────

function BulkUpload({ formats }: { formats: StatementFormat[] }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [formatId, setFormatId]           = useState<number | "">("");
  const [accountNumber, setAccountNumber] = useState("");
  const [skipPatterns, setSkipPatterns]   = useState("");
  const [year, setYear]                   = useState(new Date().getFullYear());
  const [importing, setImporting]         = useState(false);
  const [result, setResult]               = useState<BulkUploadResult | null>(null);
  const [error, setError]                 = useState<string | null>(null);

  const selectedFormat = formats.find((f) => f.id === formatId);
  const needsYear = selectedFormat?.year_source === "manual";

  function handleFiles(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    setSelectedFiles(files);
    setResult(null);
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedFiles.length) { setError("Select at least one PDF"); return; }
    if (!formatId)              { setError("Select a format"); return; }
    if (!accountNumber.trim()) { setError("Account number is required"); return; }

    setError(null);
    setImporting(true);
    try {
      const r = await bulkUpload(
        selectedFiles,
        formatId as number,
        accountNumber.trim(),
        skipPatterns,
        needsYear ? year : undefined,
      );
      setResult(r);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setImporting(false);
    }
  }

  function reset() {
    setSelectedFiles([]);
    setResult(null);
    setError(null);
    setSkipPatterns("");
    if (fileRef.current) fileRef.current.value = "";
  }

  if (result) {
    return (
      <div className="max-w-4xl space-y-5">
        <div className="bg-gray-900 rounded-xl border border-green-800 p-4 flex items-center justify-between">
          <p className="text-green-400 text-sm font-medium">
            {result.total_added} transaction{result.total_added !== 1 ? "s" : ""} imported
            {result.total_skipped > 0 && <span className="text-gray-500 font-normal"> · {result.total_skipped} duplicates skipped</span>}
            {result.total_errors > 0 && <span className="text-red-400 font-normal"> · {result.total_errors} file{result.total_errors !== 1 ? "s" : ""} failed</span>}
          </p>
          <button onClick={reset} className="text-sm text-indigo-400 hover:text-indigo-300">Upload more</button>
        </div>

        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-xs text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-2.5 text-left font-medium">File</th>
                <th className="px-4 py-2.5 text-right font-medium w-20">Added</th>
                <th className="px-4 py-2.5 text-right font-medium w-20">Skipped</th>
                <th className="px-4 py-2.5 text-right font-medium w-16">Status</th>
              </tr>
            </thead>
            <tbody>
              {result.results.map((r: BulkFileResult, i: number) => (
                <tr key={i} className="border-b border-gray-800/50 last:border-0">
                  <td className="px-4 py-2">
                    <span className="text-gray-300">{r.filename}</span>
                    {r.error && <p className="text-red-400 text-xs mt-0.5">{r.error}</p>}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-green-400">{r.error ? "—" : r.added}</td>
                  <td className="px-4 py-2 text-right tabular-nums text-gray-500">{r.error ? "—" : r.skipped}</td>
                  <td className="px-4 py-2 text-right">
                    {r.error
                      ? <span className="text-red-400 text-xs">Error</span>
                      : <span className="text-green-400 text-xs">OK</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl space-y-5">
      {/* File picker */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 flex flex-col items-center gap-4 text-center">
        <div className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center text-xl">📂</div>
        <div>
          <p className="text-sm text-gray-300 font-medium">
            {selectedFiles.length > 0 ? `${selectedFiles.length} file${selectedFiles.length !== 1 ? "s" : ""} selected` : "Select PDF statements"}
          </p>
          <p className="text-xs text-gray-500 mt-1">All files must be from the same account and format</p>
        </div>
        <label className="cursor-pointer bg-indigo-600 hover:bg-indigo-500 px-4 py-2 rounded-lg text-sm font-medium transition-colors">
          Choose files
          <input ref={fileRef} type="file" accept=".pdf" multiple onChange={handleFiles} className="hidden" />
        </label>
        {selectedFiles.length > 0 && (
          <div className="w-full text-left space-y-1 max-h-40 overflow-y-auto">
            {selectedFiles.map((f, i) => (
              <p key={i} className="text-xs text-gray-400 truncate">{f.name}</p>
            ))}
          </div>
        )}
      </div>

      {/* Format + account */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-3">
        <div>
          <label className="text-xs text-gray-400">Format *</label>
          <select
            required
            value={formatId}
            onChange={(e) => setFormatId(e.target.value ? Number(e.target.value) : "")}
            className="mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">— Select a saved format —</option>
            {formats.map((f) => (
              <option key={f.id} value={f.id}>{f.name}{f.is_builtin ? " (built-in)" : ""}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-400">Account number *</label>
          <input
            type="text"
            required
            value={accountNumber}
            onChange={(e) => setAccountNumber(e.target.value)}
            placeholder="e.g. 12345678"
            className="mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        {needsYear && (
          <div>
            <label className="text-xs text-gray-400">Statement year *</label>
            <input
              type="number"
              required
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">All selected files will use this year</p>
          </div>
        )}
      </div>

      {/* Skip patterns */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-2">
        <label className="text-xs text-gray-400 font-medium uppercase tracking-wide">Skip rows</label>
        <input
          type="text"
          value={skipPatterns}
          onChange={(e) => setSkipPatterns(e.target.value)}
          placeholder="e.g. Opening balance, Closing balance"
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
        />
        <p className="text-xs text-gray-600">Comma-separated descriptions to exclude across all files</p>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <button
        type="submit"
        disabled={importing || selectedFiles.length === 0}
        className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors"
      >
        {importing ? "Importing…" : `Import ${selectedFiles.length || ""} file${selectedFiles.length !== 1 ? "s" : ""}`}
      </button>
    </form>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

type Stage = "idle" | "previewing" | "mapping" | "importing" | "done";

export default function Upload() {
  const fileRef = useRef<HTMLInputElement>(null);

  const [tab,      setTab]      = useState<"single" | "bulk">("single");
  const [stage,    setStage]    = useState<Stage>("idle");
  const [preview,  setPreview]  = useState<PreviewResponse | null>(null);
  const [roleMap,  setRoleMap]  = useState<Record<number, ColumnRole>>({});
  const [accountNumber, setAccountNumber] = useState("");
  const [year,     setYear]     = useState(new Date().getFullYear());
  const [skipPatterns,  setSkipPatterns]  = useState("");
  const [saveFormat,    setSaveFormat]    = useState(false);
  const [formatName,    setFormatName]    = useState("");
  const [formats,  setFormats]  = useState<StatementFormat[]>([]);
  const [result,   setResult]   = useState<{ added: number; skipped: number; transactions: Transaction[] } | null>(null);
  const [error,    setError]    = useState<string | null>(null);

  useEffect(() => {
    getFormats().then(setFormats).catch(() => {});
  }, []);

  // ── Step 1: drop file ───────────────────────────────────────────────────────

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setStage("previewing");
    try {
      const data = await previewUpload(file);
      setPreview(data);
      setRoleMap(mappingToRoleMap(data.proposed_mapping));
      setAccountNumber(data.detected_account_number ?? "");
      if (data.detected_year) setYear(data.detected_year);
      if (data.matched_format) setFormatName(data.matched_format.name);
      setStage("mapping");
    } catch (err) {
      setError((err as Error).message);
      setStage("idle");
    }
  }

  // ── Step 2: confirm mapping ─────────────────────────────────────────────────

  async function handleConfirm(e: React.FormEvent) {
    e.preventDefault();
    if (!preview) return;

    const validationError = validateRoleMap(roleMap);
    if (validationError) { setError(validationError); return; }
    if (!accountNumber.trim()) { setError("Account number is required"); return; }

    setError(null);
    setStage("importing");

    const mapping = buildColumnMapping(roleMap, preview);

    try {
      const skip_patterns = skipPatterns
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      const r = await confirmUpload({
        preview_token: preview.preview_token,
        account_number: accountNumber.trim(),
        mapping,
        column_headers: preview.column_headers,
        year: preview.needs_year ? year : undefined,
        skip_patterns,
        save_format: saveFormat,
        format_name: saveFormat ? formatName : undefined,
        format_id: preview.matched_format?.id ?? undefined,
      });
      setResult({ added: r.added, skipped: r.skipped, transactions: r.transactions ?? [] });
      setStage("done");
    } catch (err) {
      setError((err as Error).message);
      setStage("mapping");
    }
  }

  function reset() {
    setStage("idle");
    setPreview(null);
    setRoleMap({});
    setAccountNumber("");
    setResult(null);
    setError(null);
    setSkipPatterns("");
    setSaveFormat(false);
    setFormatName("");
    if (fileRef.current) fileRef.current.value = "";
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  if (stage === "done" && result) {
    return (
      <div className="max-w-2xl space-y-5">
        <h1 className="text-lg font-semibold">Upload bank statement</h1>

        <div className="bg-gray-900 rounded-xl border border-green-800 p-4 flex items-center justify-between">
          <p className="text-green-400 text-sm font-medium">
            {result.added} transaction{result.added !== 1 ? "s" : ""} imported
            {result.skipped > 0 && <span className="text-gray-500 font-normal"> · {result.skipped} duplicates skipped</span>}
          </p>
          <button onClick={reset} className="text-sm text-indigo-400 hover:text-indigo-300">
            Upload another
          </button>
        </div>

        {result.transactions.length > 0 && (
          <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-xs text-gray-500 uppercase tracking-wide">
                  <th className="px-4 py-2.5 text-left font-medium">Date</th>
                  <th className="px-4 py-2.5 text-left font-medium">Description</th>
                  <th className="px-4 py-2.5 text-right font-medium">Amount</th>
                </tr>
              </thead>
              <tbody>
                {result.transactions.map((t) => (
                  <tr key={t.id} className="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/30">
                    <td className="px-4 py-2 text-gray-400 whitespace-nowrap">{t.date}</td>
                    <td className="px-4 py-2 text-gray-300 truncate max-w-[280px]">{t.description}</td>
                    <td className={`px-4 py-2 text-right tabular-nums font-medium ${t.amount >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {t.amount >= 0 ? "+" : ""}£{Math.abs(t.amount).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }

  if (stage === "previewing") {
    return (
      <div className="max-w-lg space-y-6">
        <h1 className="text-lg font-semibold">Upload bank statement</h1>
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-8 flex flex-col items-center gap-3">
          <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-gray-400">Analysing statement…</p>
        </div>
      </div>
    );
  }

  if ((stage === "mapping" || stage === "importing") && preview) {
    const { matched_format, confidence, column_headers, sample_rows, needs_year, total_rows } = preview;

    return (
      <div className="max-w-3xl space-y-6">
        <h1 className="text-lg font-semibold">Upload bank statement</h1>

        {/* Format selector */}
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 flex items-center gap-4">
          <div className="flex items-center gap-2 shrink-0">
            {matched_format ? (
              <span className="text-xs font-medium bg-green-900 text-green-300 px-2 py-0.5 rounded-full">
                Matched {Math.round(confidence * 100)}%
              </span>
            ) : (
              <span className="text-xs font-medium bg-yellow-900 text-yellow-300 px-2 py-0.5 rounded-full">
                New
              </span>
            )}
          </div>

          <select
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm"
            value={matched_format?.id ?? ""}
            onChange={(e) => {
              if (!e.target.value) return;
              const fmt = formats.find((f) => f.id === Number(e.target.value));
              if (fmt) setRoleMap(formatToRoleMap(fmt));
            }}
          >
            <option value="">— Apply a saved format —</option>
            {formats.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}{f.is_builtin ? " (built-in)" : ""}
              </option>
            ))}
          </select>

          <span className="text-xs text-gray-500 shrink-0">{total_rows} rows</span>
        </div>

        <form onSubmit={handleConfirm} className="space-y-5">
          {/* Account number + year */}
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-400">Account number *</label>
              <input
                type="text"
                required
                value={accountNumber}
                onChange={(e) => setAccountNumber(e.target.value)}
                placeholder="e.g. 12345678"
                className="mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            {needs_year && (
              <div>
                <label className="text-xs text-gray-400">Statement year *</label>
                <input
                  type="number"
                  required
                  value={year}
                  onChange={(e) => setYear(Number(e.target.value))}
                  className="mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
                />
                <p className="text-xs text-gray-500 mt-1">Dates in this PDF have no year</p>
              </div>
            )}
          </div>

          {/* Column mapping table */}
          <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-x-auto">
            <div className="px-4 py-3 border-b border-gray-800">
              <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">Column mapping</p>
              <p className="text-xs text-gray-600 mt-0.5">Assign a role to each column. Sample rows shown below.</p>
            </div>
            <table className="w-full text-xs">
              <thead>
                <tr>
                  {column_headers.map((header, colIdx) => (
                    <th key={colIdx} className="px-3 pt-3 pb-2 text-left align-top font-normal min-w-[120px]">
                      <div className="text-gray-300 font-medium mb-1.5 truncate" title={header}>
                        {header || `Col ${colIdx}`}
                      </div>
                      <select
                        value={roleMap[colIdx] ?? "ignore"}
                        onChange={(e) =>
                          setRoleMap((prev) => ({ ...prev, [colIdx]: e.target.value as ColumnRole }))
                        }
                        className={`w-full bg-gray-800 border border-gray-700 rounded px-1.5 py-1 text-xs ${roleColor(roleMap[colIdx] ?? "ignore")}`}
                      >
                        {ROLES.map((r) => (
                          <option key={r.value} value={r.value} className="text-gray-200">
                            {r.label}
                          </option>
                        ))}
                      </select>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sample_rows.map((row, rowIdx) => (
                  <tr key={rowIdx} className={rowIdx % 2 === 0 ? "bg-gray-900" : "bg-gray-800/40"}>
                    {column_headers.map((_, colIdx) => (
                      <td
                        key={colIdx}
                        className={`px-3 py-1.5 max-w-[180px] truncate ${roleColor(roleMap[colIdx] ?? "ignore")}`}
                        title={row[colIdx] ?? ""}
                      >
                        {row[colIdx] ?? ""}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Skip patterns */}
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-2">
            <label className="text-xs text-gray-400 font-medium uppercase tracking-wide">
              Skip rows
            </label>
            <input
              type="text"
              value={skipPatterns}
              onChange={(e) => setSkipPatterns(e.target.value)}
              placeholder="e.g. Opening balance, Closing balance, Transfer"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
            />
            <p className="text-xs text-gray-600">
              Comma-separated descriptions to exclude. Rows with no amount are already skipped automatically.
            </p>
          </div>

          {/* Save format */}
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-3">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={saveFormat}
                onChange={(e) => setSaveFormat(e.target.checked)}
                className="rounded border-gray-600 bg-gray-700 text-indigo-500"
              />
              <span className="text-sm text-gray-300">Save this column mapping for future uploads</span>
            </label>
            {saveFormat && (
              <input
                type="text"
                placeholder="Format name, e.g. Monzo or HSBC Current"
                value={formatName}
                onChange={(e) => setFormatName(e.target.value)}
                required={saveFormat}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
              />
            )}
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <div className="flex gap-3">
            <button
              type="button"
              onClick={reset}
              className="px-4 py-2.5 rounded-lg text-sm border border-gray-700 hover:bg-gray-800 transition-colors"
            >
              Back
            </button>
            <button
              type="submit"
              disabled={stage === "importing"}
              className="flex-1 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors"
            >
              {stage === "importing" ? "Importing…" : `Import ${total_rows} rows`}
            </button>
          </div>
        </form>
      </div>
    );
  }

  // Default: idle — file drop (single) or bulk
  return (
    <div className="max-w-lg space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Upload bank statement</h1>
        <div className="flex rounded-lg border border-gray-700 overflow-hidden text-sm">
          <button
            onClick={() => setTab("single")}
            className={`px-3 py-1.5 transition-colors ${tab === "single" ? "bg-gray-700 text-white" : "text-gray-400 hover:text-gray-200"}`}
          >
            Single
          </button>
          <button
            onClick={() => setTab("bulk")}
            className={`px-3 py-1.5 transition-colors ${tab === "bulk" ? "bg-gray-700 text-white" : "text-gray-400 hover:text-gray-200"}`}
          >
            Bulk
          </button>
        </div>
      </div>

      {tab === "bulk" ? (
        <BulkUpload formats={formats} />
      ) : (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-8 flex flex-col items-center gap-4 text-center">
          <div className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center text-xl">
            📄
          </div>
          <div>
            <p className="text-sm text-gray-300 font-medium">Drop a PDF statement</p>
            <p className="text-xs text-gray-500 mt-1">Any bank — column mapping is detected automatically</p>
          </div>
          <label className="cursor-pointer bg-indigo-600 hover:bg-indigo-500 px-4 py-2 rounded-lg text-sm font-medium transition-colors">
            Choose file
            <input
              ref={fileRef}
              type="file"
              accept=".pdf"
              onChange={handleFile}
              className="hidden"
            />
          </label>
          {error && <p className="text-sm text-red-400">{error}</p>}
        </div>
      )}
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import {
  createTemplate,
  deleteTemplate,
  extractTables,
  getTemplates,
} from "../api/client";
import type { ColumnRole, ExtractedTable, UserParserTemplate } from "../types";

// ── Column role helpers ───────────────────────────────────────────────────────

const STATEMENT_ROLES: { value: ColumnRole; label: string; color: string }[] = [
  { value: "date", label: "Date", color: "text-blue-400" },
  { value: "description", label: "Description", color: "text-purple-400" },
  {
    value: "date_description",
    label: "Date + Description",
    color: "text-cyan-400",
  },
  { value: "money_in", label: "Money In", color: "text-green-400" },
  { value: "money_out", label: "Money Out", color: "text-red-400" },
  { value: "amount", label: "Amount (±)", color: "text-yellow-400" },
  { value: "balance", label: "Balance", color: "text-slate-400" },
  { value: "ignore", label: "Ignore", color: "text-slate-600" },
];

const PAYSLIP_ROLES: { value: ColumnRole; label: string; color: string }[] = [
  { value: "description", label: "Description", color: "text-purple-400" },
  { value: "amount", label: "Amount", color: "text-yellow-400" },
  { value: "ignore", label: "Ignore", color: "text-slate-600" },
];

function roleColor(role: string, roles: typeof STATEMENT_ROLES) {
  return roles.find((r) => r.value === role)?.color ?? "text-slate-400";
}

const DATE_FORMAT_OPTIONS: {
  value: string;
  label: string;
  year_source: "inline" | "detect";
}[] = [
  { value: "%d %b %Y", label: "01 Jan 2024 (Chase UK)", year_source: "inline" },
  {
    value: "%d/%m/%Y",
    label: "01/01/2024 (Barclays, most UK banks)",
    year_source: "inline",
  },
  { value: "%Y-%m-%d", label: "2024-01-01 (ISO)", year_source: "inline" },
  { value: "%d-%m-%Y", label: "01-01-2024", year_source: "inline" },
  { value: "%d/%m/%y", label: "01/01/24 (short year)", year_source: "inline" },
  {
    value: "%d %b",
    label: "01 Jan (Barclays PDF — year auto-detected)",
    year_source: "detect",
  },
];

function roleMapToMapping(
  roleMap: Record<number, ColumnRole>,
  templateType: "statement" | "payslip",
  dateFormat: string,
) {
  const first = (role: ColumnRole) => {
    const e = Object.entries(roleMap).find(([, r]) => r === role);
    return e != null ? Number(e[0]) : null;
  };

  if (templateType === "payslip") {
    return {
      description_col: first("description"),
      amount_col: first("amount"),
      date_col: null,
      date_description_col: null,
      balance_col: null,
      amount_style: "signed" as const,
      money_in_col: null,
      money_out_col: null,
      date_format: null,
      year_source: "inline" as const,
    };
  }

  const hasIn = first("money_in") != null;
  const hasOut = first("money_out") != null;
  const amount_style: "split" | "signed" = hasIn || hasOut ? "split" : "signed";
  const fmtOption =
    DATE_FORMAT_OPTIONS.find((o) => o.value === dateFormat) ??
    DATE_FORMAT_OPTIONS[0];

  return {
    date_col: first("date"),
    description_col: first("description"),
    date_description_col: first("date_description"),
    balance_col: first("balance"),
    amount_style,
    amount_col: amount_style === "signed" ? first("amount") : null,
    money_in_col: amount_style === "split" ? first("money_in") : null,
    money_out_col: amount_style === "split" ? first("money_out") : null,
    date_format: dateFormat,
    year_source: fmtOption.year_source,
  };
}

function validateRoleMap(
  roleMap: Record<number, ColumnRole>,
  templateType: "statement" | "payslip",
): string | null {
  const roles = Object.values(roleMap);
  if (templateType === "payslip") {
    if (!roles.includes("description")) return "Assign a Description column";
    if (!roles.includes("amount")) return "Assign an Amount column";
    return null;
  }
  const hasMerged = roles.includes("date_description");
  if (!hasMerged && !roles.includes("date"))
    return "Assign a Date column (or Date + Description)";
  if (!hasMerged && !roles.includes("description"))
    return "Assign a Description column (or Date + Description)";
  if (
    !roles.includes("amount") &&
    !roles.includes("money_in") &&
    !roles.includes("money_out")
  )
    return "Assign at least one amount column";
  return null;
}

// ── Row classification ────────────────────────────────────────────────────────

// * → glob full-match (case-sensitive); otherwise exact full-match. Pattern must not include trailing |.
function matchesSkip(desc: string, pattern: string): boolean {
  if (pattern.includes("*")) {
    const regex = new RegExp(
      "^" +
        pattern.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*") +
        "$",
    );
    return regex.test(desc);
  }
  return desc === pattern;
}

type RowKind = "normal" | "boundary" | "deduction" | "skipped";

function classifyRows(
  rows: string[][],
  roleMap: Record<number, ColumnRole>,
  previewBoundary: string,
  previewSkips: string[],
): RowKind[] {
  const descIdx = Number(
    Object.entries(roleMap).find(
      ([, r]) => r === "description" || r === "date_description",
    )?.[0] ?? -1,
  );
  const boundaryKw = previewBoundary.trim();
  const normalSkips = previewSkips.filter((p) => !p.endsWith("|"));
  const cutoffSkips = previewSkips
    .filter((p) => p.endsWith("|"))
    .map((p) => p.slice(0, -1));
  const kinds: RowKind[] = [];
  let pastBoundary = false;
  let pastCutoff = false;

  for (const row of rows) {
    if (pastCutoff) {
      kinds.push("skipped");
      continue;
    }
    if (boundaryKw && row.some((c) => c.trim() === boundaryKw)) {
      kinds.push("boundary");
      pastBoundary = true;
      continue;
    }
    if (descIdx >= 0) {
      const desc = (row[descIdx] ?? "").trim();
      if (cutoffSkips.some((p) => matchesSkip(desc, p))) {
        pastCutoff = true;
        kinds.push("skipped");
        continue;
      }
      if (normalSkips.some((p) => matchesSkip(desc, p))) {
        kinds.push("skipped");
        continue;
      }
    }
    kinds.push(pastBoundary ? "deduction" : "normal");
  }
  return kinds;
}

// ── Column mapping UI ─────────────────────────────────────────────────────────

function ColumnMappingEditor({
  table,
  roleMap,
  onChange,
  templateType,
  previewBoundary,
  previewSkips,
}: {
  table: ExtractedTable;
  roleMap: Record<number, ColumnRole>;
  onChange: (m: Record<number, ColumnRole>) => void;
  templateType: "statement" | "payslip";
  previewBoundary: string;
  previewSkips: string[];
}) {
  const roles = templateType === "payslip" ? PAYSLIP_ROLES : STATEMENT_ROLES;
  const rowKinds = classifyRows(
    table.sample_rows,
    roleMap,
    previewBoundary,
    previewSkips,
  );

  function cellClass(colIdx: number, kind: RowKind): string {
    if (kind === "skipped") return "text-slate-600";
    if (kind === "boundary") return "text-amber-400";
    const role = roleMap[colIdx] ?? "ignore";
    if (
      kind === "deduction" &&
      (role === "amount" || role === "money_out" || role === "money_in")
    ) {
      return "text-red-400";
    }
    return roleColor(role, roles);
  }

  return (
    <div className="rounded-xl border border-slate-800 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 z-10 bg-slate-900">
            <tr>
              {table.headers.map((header, colIdx) => (
                <th
                  key={colIdx}
                  className="px-3 pt-3 pb-2 text-left align-top font-normal min-w-[120px] border-b border-slate-800"
                >
                  <div
                    className="text-slate-300 font-medium mb-1.5 truncate"
                    title={header}
                  >
                    {header || `Col ${colIdx}`}
                  </div>
                  <select
                    value={roleMap[colIdx] ?? "ignore"}
                    onChange={(e) =>
                      onChange({
                        ...roleMap,
                        [colIdx]: e.target.value as ColumnRole,
                      })
                    }
                    className={`w-full bg-slate-800 border border-slate-700 rounded px-1.5 py-1 text-xs ${roleColor(roleMap[colIdx] ?? "ignore", roles)}`}
                  >
                    {roles.map((r) => (
                      <option
                        key={r.value}
                        value={r.value}
                        className="text-slate-200"
                      >
                        {r.label}
                      </option>
                    ))}
                  </select>
                </th>
              ))}
            </tr>
          </thead>
        </table>
      </div>
      <div className="overflow-x-auto overflow-y-auto max-h-[60vh]">
        <table className="w-full text-xs">
          <tbody>
            {table.sample_rows.map((row, rowIdx) => {
              const kind = rowKinds[rowIdx] ?? "normal";
              const isSkipped = kind === "skipped";
              const isBoundary = kind === "boundary";
              return (
                <tr
                  key={rowIdx}
                  className={
                    isBoundary
                      ? "bg-amber-950/40 border-t border-b border-amber-800/50"
                      : isSkipped
                        ? "opacity-40"
                        : rowIdx % 2 === 0
                          ? "bg-slate-900"
                          : "bg-slate-800/40"
                  }
                >
                  {table.headers.map((_, colIdx) => (
                    <td
                      key={colIdx}
                      className={`px-3 py-1.5 min-w-[120px] max-w-[240px] truncate ${cellClass(colIdx, kind)}`}
                      title={row[colIdx] ?? ""}
                    >
                      {row[colIdx] ?? ""}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Create template wizard ────────────────────────────────────────────────────

type WizardStep = "upload" | "map" | "save";

function CreateWizard({ onDone }: { onDone: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);

  const [templateType, setTemplateType] = useState<"statement" | "payslip">(
    "statement",
  );
  const [fileType, setFileType] = useState<"pdf" | "csv">("pdf");
  const [step, setStep] = useState<WizardStep>("upload");
  const [extracting, setExtracting] = useState(false);
  const [tables, setTables] = useState<ExtractedTable[]>([]);
  const [selectedTable, setSelectedTable] = useState(0);
  const [roleMap, setRoleMap] = useState<Record<number, ColumnRole>>({});
  const [skipPatterns, setSkipPatterns] = useState("");
  const [deductionBoundary, setDeductionBoundary] = useState("");
  const [dateFormat, setDateFormat] = useState("%d %b %Y");
  const [previewBoundary, setPreviewBoundary] = useState("");
  const [previewSkips, setPreviewSkips] = useState<string[]>([]);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setExtracting(true);
    try {
      const res = await extractTables(file);
      if (!res.tables.length) throw new Error("No tables found in this file");
      setTables(res.tables);
      setSelectedTable(0);
      setRoleMap({});
      setDeductionBoundary("");
      setDateFormat("%d %b %Y");
      setPreviewBoundary("");
      setPreviewSkips([]);
      setStep("map");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setExtracting(false);
    }
  }

  async function handleSave() {
    const validationError = validateRoleMap(roleMap, templateType);
    if (validationError) {
      setError(validationError);
      return;
    }
    if (!name.trim()) {
      setError("Give the template a name");
      return;
    }

    const table = tables[selectedTable];
    const mapping = roleMapToMapping(roleMap, templateType, dateFormat);
    const patterns = skipPatterns
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    setSaving(true);
    setError(null);
    try {
      await createTemplate({
        name: name.trim(),
        template_type: templateType,
        file_type: fileType,
        table_index: selectedTable,
        column_headers: table.headers,
        skip_patterns: patterns,
        deduction_boundary_keyword:
          templateType === "payslip" && deductionBoundary.trim()
            ? deductionBoundary.trim()
            : null,
        ...mapping,
      });
      onDone();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (step === "upload") {
    return (
      <div className="max-w-lg space-y-5">
        <h2 className="text-base font-semibold">New template</h2>

        {/* Type + file type */}
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-4 space-y-4">
          <div>
            <p className="text-xs text-slate-400 mb-2">Template type</p>
            <div className="flex gap-2">
              {(["statement", "payslip"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTemplateType(t)}
                  className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                    templateType === t
                      ? "bg-indigo-600 border-indigo-600 text-white"
                      : "border-slate-700 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {t === "statement" ? "Bank statement" : "Payslip"}
                </button>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs text-slate-400 mb-2">File type</p>
            <div className="flex gap-2">
              {(["pdf", "csv"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setFileType(t)}
                  className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                    fileType === t
                      ? "bg-indigo-600 border-indigo-600 text-white"
                      : "border-slate-700 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {t.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* File picker */}
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-8 flex flex-col items-center gap-4 text-center">
          <p className="text-sm text-slate-300 font-medium">
            Upload a sample {fileType.toUpperCase()} file
          </p>
          <p className="text-xs text-slate-500">
            Used to extract tables — nothing will be imported
          </p>
          <label className="cursor-pointer bg-indigo-600 hover:bg-indigo-500 px-4 py-2 rounded-lg text-sm font-medium transition-colors">
            {extracting ? "Extracting…" : "Choose file"}
            <input
              ref={fileRef}
              type="file"
              accept={fileType === "pdf" ? ".pdf" : ".csv"}
              onChange={handleFile}
              disabled={extracting}
              className="hidden"
            />
          </label>
          {error && <p className="text-sm text-red-400">{error}</p>}
        </div>
      </div>
    );
  }

  const currentTable = tables[selectedTable];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setStep("upload")}
          className="text-sm text-slate-400 hover:text-slate-200"
        >
          ← Back
        </button>
        <h2 className="text-base font-semibold">New template</h2>
        <span className="text-xs bg-indigo-900/50 text-indigo-300 px-2 py-0.5 rounded-full">
          {templateType === "statement" ? "Bank statement" : "Payslip"}
        </span>
      </div>

      {/* Table selector (only shown when multiple tables) */}
      {tables.length > 1 && (
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-4 space-y-2">
          <p className="text-xs text-slate-400 font-medium uppercase tracking-wide">
            Select table ({tables.length} found)
          </p>
          <div className="flex flex-wrap gap-2">
            {tables.map((t, i) => (
              <button
                key={i}
                onClick={() => {
                  setSelectedTable(i);
                  setRoleMap({});
                }}
                className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                  selectedTable === i
                    ? "bg-indigo-600 border-indigo-600 text-white"
                    : "border-slate-700 text-slate-400 hover:text-slate-200"
                }`}
              >
                Table {i + 1}{" "}
                <span className="text-xs opacity-60">
                  ({t.total_rows} rows, {t.headers.length} cols)
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Two-column layout: table left, config right */}
      <div className="flex gap-5 items-start">
        {/* Left: column mapping table */}
        <div className="flex-1 min-w-0 bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-800">
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wide">
              Column mapping
            </p>
            <p className="text-xs text-slate-600 mt-0.5">
              Assign a role to each column
            </p>
          </div>
          <div className="p-1">
            <ColumnMappingEditor
              table={currentTable}
              roleMap={roleMap}
              onChange={setRoleMap}
              templateType={templateType}
              previewBoundary={previewBoundary}
              previewSkips={previewSkips}
            />
          </div>
        </div>

        {/* Right: config + save (sticky) */}
        <div className="w-72 shrink-0 sticky top-4 space-y-3">
          {/* Date format (statements only) */}
          {templateType === "statement" && (
            <div className="bg-slate-900 rounded-xl border border-slate-800 p-4 space-y-2">
              <label className="text-xs text-slate-400 font-medium uppercase tracking-wide">
                Date format
              </label>
              <select
                value={dateFormat}
                onChange={(e) => setDateFormat(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200"
              >
                {DATE_FORMAT_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
              <p className="text-xs text-slate-600">
                Match the date format in your file's date column
              </p>
            </div>
          )}

          {/* Deduction boundary (payslips only) */}
          {templateType === "payslip" && (
            <div className="bg-slate-900 rounded-xl border border-slate-800 p-4 space-y-2">
              <label className="text-xs text-slate-400 font-medium uppercase tracking-wide">
                Deductions boundary
              </label>
              <input
                type="text"
                value={deductionBoundary}
                onChange={(e) => setDeductionBoundary(e.target.value)}
                onBlur={() => setPreviewBoundary(deductionBoundary.trim())}
                placeholder="e.g. TOTAL"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
              />
              <p className="text-xs text-slate-600">
                Rows after this keyword are deductions. Leave blank to use
                amount sign. Use <span className="text-slate-400">TOTAL</span>{" "}
                for NordHealth.
              </p>
            </div>
          )}

          {/* Skip patterns */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-4 space-y-2">
            <label className="text-xs text-slate-400 font-medium uppercase tracking-wide">
              Skip rows
            </label>
            <input
              type="text"
              value={skipPatterns}
              onChange={(e) => setSkipPatterns(e.target.value)}
              onBlur={() =>
                setPreviewSkips(
                  skipPatterns
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean),
                )
              }
              placeholder={
                templateType === "payslip"
                  ? "e.g. Ers NIC, NET PAY"
                  : "e.g. Opening balance"
              }
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
            />
            <p className="text-xs text-slate-600">
              Comma-separated, case-sensitive. Plain text matches the exact
              description. Add <span className="text-slate-400">*</span> to
              match a prefix (e.g.{" "}
              <span className="text-slate-400">Ers NIC*</span> matches{" "}
              <em>Ers NIC TP: 1,164.23</em>). Append{" "}
              <span className="text-slate-400">|</span> to also skip all rows
              after the match (e.g.{" "}
              <span className="text-slate-400">
                Total taxable pay to date*|
              </span>
              ).
            </p>
          </div>

          {/* Name + save */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-4 space-y-3">
            <label className="text-xs text-slate-400 font-medium uppercase tracking-wide">
              Template name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={
                templateType === "statement"
                  ? "e.g. Barclays, Chase, Monzo"
                  : "e.g. NordHealth payslip"
              }
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
            />
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors"
          >
            {saving ? "Saving…" : "Save template"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function Templates() {
  const [templates, setTemplates] = useState<UserParserTemplate[]>([]);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const data = await getTemplates();
      setTemplates(data);
    } catch {
      setError("Failed to load templates");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleDelete(id: number) {
    setDeleting(id);
    try {
      await deleteTemplate(id);
      setTemplates((prev) => prev.filter((t) => t.id !== id));
    } catch {
      setError("Failed to delete template");
    } finally {
      setDeleting(null);
    }
  }

  if (creating) {
    return (
      <div className="space-y-6">
        <CreateWizard
          onDone={() => {
            setCreating(false);
            load();
          }}
        />
      </div>
    );
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Parser templates</h1>
        <button
          onClick={() => setCreating(true)}
          className="bg-indigo-600 hover:bg-indigo-500 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          New template
        </button>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {templates.length === 0 ? (
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-10 text-center">
          <p className="text-slate-400 text-sm">No templates yet.</p>
          <p className="text-slate-600 text-xs mt-1">
            Create a template to define how your bank statements or payslips are
            parsed.
          </p>
          <button
            onClick={() => setCreating(true)}
            className="mt-4 bg-indigo-600 hover:bg-indigo-500 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Create first template
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {templates.map((t) => (
            <div
              key={t.id}
              className="bg-slate-900 rounded-xl border border-slate-800 p-4 flex items-center gap-4"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-slate-200">
                    {t.name}
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      t.template_type === "statement"
                        ? "bg-sky-900/50 text-sky-300"
                        : "bg-violet-900/50 text-violet-300"
                    }`}
                  >
                    {t.template_type === "statement" ? "Statement" : "Payslip"}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-slate-800 text-slate-400">
                    {t.file_type.toUpperCase()}
                  </span>
                </div>
                <p className="text-xs text-slate-500">
                  {t.column_headers ? t.column_headers.length : "?"} columns
                  {t.skip_patterns.length > 0 &&
                    ` · skips: ${t.skip_patterns.join(", ")}`}
                </p>
              </div>
              <button
                onClick={() => handleDelete(t.id)}
                disabled={deleting === t.id}
                className="text-sm text-slate-500 hover:text-red-400 transition-colors disabled:opacity-50 shrink-0"
              >
                {deleting === t.id ? "…" : "Delete"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { getSalaries, createSalary, deleteSalary, uploadPayslip, bulkUploadPayslips, getIdentities } from "../api/client";
import type { Salary, PayslipLineItem, PersonIdentity } from "../types";

const emptyForm = {
  date: "",
  net_amount: "",
  gross_amount: "",
  employer: "",
  notes: "",
};

function fmt(n: number) {
  return `£${n.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function LineItemsTable({ items }: { items: PayslipLineItem[] }) {
  const earnings = items.filter((i) => i.line_type === "earning");
  const deductions = items.filter((i) => i.line_type === "deduction");

  const Section = ({
    title,
    rows,
    colorClass,
  }: {
    title: string;
    rows: PayslipLineItem[];
    colorClass: string;
  }) => (
    <>
      <tr className="bg-gray-800/60">
        <td colSpan={4} className={`px-4 py-1 text-xs font-semibold uppercase tracking-wider ${colorClass}`}>
          {title}
        </td>
      </tr>
      {rows.map((item) => (
        <tr key={item.id} className="border-t border-gray-800/30">
          <td className="px-4 py-1.5 text-sm text-gray-300 pl-6">{item.description}</td>
          <td className="px-4 py-1.5 text-xs text-gray-500 text-right">
            {item.rate != null ? fmt(item.rate) : ""}
            {item.units ? <span className="ml-1 text-gray-600">× {item.units}</span> : null}
          </td>
          <td className={`px-4 py-1.5 text-sm text-right font-medium ${colorClass}`}>
            {fmt(item.amount)}
          </td>
          <td className="px-4 py-1.5 text-xs text-right text-gray-600">
            {item.this_year_amount != null ? fmt(item.this_year_amount) : ""}
          </td>
        </tr>
      ))}
    </>
  );

  return (
    <table className="w-full text-sm bg-gray-950/60">
      <thead>
        <tr className="text-xs text-gray-500 border-b border-gray-800">
          <th className="px-4 py-2 text-left pl-6">Description</th>
          <th className="px-4 py-2 text-right">Rate / Units</th>
          <th className="px-4 py-2 text-right">This period</th>
          <th className="px-4 py-2 text-right">This year</th>
        </tr>
      </thead>
      <tbody>
        {earnings.length > 0 && (
          <Section title="Earnings" rows={earnings} colorClass="text-green-400" />
        )}
        {deductions.length > 0 && (
          <Section title="Deductions" rows={deductions} colorClass="text-red-400" />
        )}
      </tbody>
    </table>
  );
}

export default function Salaries() {
  const [salaries, setSalaries] = useState<Salary[]>([]);
  const [identities, setIdentities] = useState<PersonIdentity[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [bulkResults, setBulkResults] = useState<{ filename: string; status: string; detail?: string; date?: string; net?: number }[] | null>(null);
  const [bulkRunning, setBulkRunning] = useState(false);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const fileInputRef = useRef<HTMLInputElement>(null);
  const bulkInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getSalaries().then(setSalaries);
    getIdentities().then(setIdentities);
  }, []);

  const nameFor = (s: Salary) => {
    if (s.ni_number) {
      const identity = identities.find((i) => i.ni_number === s.ni_number);
      if (identity) return identity.display_name;
      return s.ni_number;
    }
    return null;
  };

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
    setExpanded((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadError(null);
    setUploading(true);
    try {
      const created = await uploadPayslip(file);
      setSalaries((prev) => {
        const without = prev.filter((s) => s.id !== created.id);
        return [created, ...without].sort(
          (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
        );
      });
      // Auto-expand the newly imported payslip
      if (created.line_items.length > 0) {
        setExpanded((prev) => new Set([...prev, created.id]));
      }
    } catch (err) {
      setUploadError((err as Error).message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleBulkUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (!files.length) return;
    setBulkResults(null);
    setBulkRunning(true);
    try {
      const res = await bulkUploadPayslips(files);
      setBulkResults(res.results);
      if (res.imported > 0) {
        // Reload full list so new entries appear
        getSalaries().then(setSalaries);
      }
    } catch (err) {
      setBulkResults([{ filename: "—", status: "error", detail: (err as Error).message }]);
    } finally {
      setBulkRunning(false);
      if (bulkInputRef.current) bulkInputRef.current.value = "";
    }
  };

  const toggleExpand = (id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const totalNet = salaries.reduce((s, r) => s + r.net_amount, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-baseline gap-4">
        <h1 className="text-lg font-semibold">Salaries / payslips</h1>
        <span className="text-sm text-gray-400">
          {salaries.length} entries · total net:{" "}
          <span className="text-green-400">£{totalNet.toLocaleString()}</span>
        </span>
      </div>

      {/* Upload payslip PDF */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5 space-y-3">
        <h2 className="text-sm font-medium text-gray-300">Upload payslip PDF</h2>
        {uploadError && <p className="text-sm text-red-400">{uploadError}</p>}
        <div className="flex items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={handleUpload}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="bg-blue-700 hover:bg-blue-600 disabled:opacity-50 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            {uploading ? "Parsing…" : "Choose PDF…"}
          </button>
          <span className="text-xs text-gray-500">
            Extracts all line items automatically
          </span>
        </div>
      </div>

      {/* Bulk import (one-time) */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5 space-y-3">
        <div className="flex items-baseline gap-3">
          <h2 className="text-sm font-medium text-gray-300">Bulk import payslips</h2>
          <span className="text-xs text-gray-600">Select all PDFs at once</span>
        </div>
        <div className="flex items-center gap-3">
          <input
            ref={bulkInputRef}
            type="file"
            accept=".pdf"
            multiple
            className="hidden"
            onChange={handleBulkUpload}
          />
          <button
            onClick={() => bulkInputRef.current?.click()}
            disabled={bulkRunning}
            className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            {bulkRunning ? "Importing…" : "Choose PDFs…"}
          </button>
          {bulkRunning && <span className="text-xs text-gray-500">Parsing PDFs, this may take a moment…</span>}
        </div>
        {bulkResults && (
          <div className="mt-2 space-y-1 max-h-64 overflow-y-auto">
            <p className="text-xs text-gray-400 mb-2">
              {bulkResults.filter((r) => r.status === "imported").length} imported ·{" "}
              {bulkResults.filter((r) => r.status === "skipped").length} skipped ·{" "}
              {bulkResults.filter((r) => r.status === "error").length} errors
            </p>
            {bulkResults.map((r, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                <span
                  className={
                    r.status === "imported"
                      ? "text-green-400"
                      : r.status === "skipped"
                      ? "text-gray-500"
                      : "text-red-400"
                  }
                >
                  {r.status === "imported" ? "✓" : r.status === "skipped" ? "–" : "✗"}
                </span>
                <span className="text-gray-400 truncate max-w-xs">{r.filename}</span>
                {r.status === "imported" && r.date && (
                  <span className="text-gray-600">
                    {new Date(r.date).toLocaleDateString("en-GB")} · {r.net != null ? fmt(r.net) : ""}
                  </span>
                )}
                {r.detail && r.status !== "imported" && (
                  <span className="text-gray-600 italic">{r.detail}</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Manual add form */}
      <form onSubmit={handleSubmit} className="bg-gray-900 rounded-xl border border-gray-800 p-5 space-y-4">
        <h2 className="text-sm font-medium text-gray-300">Add payslip manually</h2>
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
              <th className="px-4 py-3 w-6"></th>
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Person</th>
              <th className="px-4 py-3">Employer</th>
              <th className="px-4 py-3 text-right">Gross</th>
              <th className="px-4 py-3 text-right">Net</th>
              <th className="px-4 py-3">Notes</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {salaries.map((s) => (
              <>
                <tr
                  key={s.id}
                  className="border-b border-gray-800/50 hover:bg-gray-800/40 cursor-pointer"
                  onClick={() => s.line_items.length > 0 && toggleExpand(s.id)}
                >
                  <td className="px-4 py-3 text-gray-600 text-xs select-none">
                    {s.line_items.length > 0 ? (expanded.has(s.id) ? "▾" : "▸") : ""}
                  </td>
                  <td className="px-4 py-3">{new Date(s.date).toLocaleDateString("en-GB")}</td>
                  <td className="px-4 py-3">
                    {nameFor(s) ? (
                      <span className="text-blue-400 text-sm">{nameFor(s)}</span>
                    ) : (
                      <span className="text-gray-600 text-xs">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-300">{s.employer ?? "—"}</td>
                  <td className="px-4 py-3 text-right text-gray-400">
                    {s.gross_amount != null ? fmt(s.gross_amount) : "—"}
                  </td>
                  <td className="px-4 py-3 text-right text-green-400 font-medium">
                    {fmt(s.net_amount)}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{s.notes ?? ""}</td>
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => handleDelete(s.id)}
                      className="text-xs text-gray-600 hover:text-red-400"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
                {expanded.has(s.id) && s.line_items.length > 0 && (
                  <tr key={`${s.id}-items`} className="border-b border-gray-800">
                    <td colSpan={8} className="p-0">
                      <LineItemsTable items={s.line_items} />
                    </td>
                  </tr>
                )}
              </>
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

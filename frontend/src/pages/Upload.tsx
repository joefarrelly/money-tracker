import { useState, useRef } from "react";
import { uploadStatement } from "../api/client";

const BANKS = ["barclays", "chase"];

export default function Upload() {
  const [bank, setBank] = useState("barclays");
  const [accountNumber, setAccountNumber] = useState("");
  const [year, setYear] = useState(new Date().getFullYear().toString());
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{ added: number; skipped: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    // Auto-detect bank from filename
    if (f) {
      const name = f.name.toLowerCase();
      if (name.includes("chase")) setBank("chase");
      else if (name.includes("barclays") || name.startsWith("statement")) setBank("barclays");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !accountNumber) return;

    setError(null);
    setResult(null);
    setUploading(true);

    const fd = new FormData();
    fd.append("file", file);
    fd.append("bank", bank);
    fd.append("account_number", accountNumber);
    if (bank === "barclays") fd.append("year", year);

    try {
      const r = await uploadStatement(fd);
      setResult({ added: r.added, skipped: r.skipped });
      setFile(null);
      setAccountNumber("");
      if (fileRef.current) fileRef.current.value = "";
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="text-lg font-semibold">Upload bank statement</h1>

      <form onSubmit={handleSubmit} className="bg-gray-900 rounded-xl border border-gray-800 p-5 space-y-4">
        {/* File */}
        <div>
          <label className="text-xs text-gray-400">PDF statement *</label>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf"
            required
            onChange={handleFile}
            className="mt-1 w-full text-sm text-gray-300 file:mr-3 file:bg-gray-700 file:border-0 file:rounded file:px-3 file:py-1.5 file:text-sm file:text-gray-200 hover:file:bg-gray-600"
          />
          {file && <p className="text-xs text-gray-500 mt-1">{file.name}</p>}
        </div>

        {/* Bank */}
        <div>
          <label className="text-xs text-gray-400">Bank *</label>
          <select
            value={bank}
            onChange={(e) => setBank(e.target.value)}
            className="mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
          >
            {BANKS.map((b) => (
              <option key={b} value={b} className="capitalize">{b.charAt(0).toUpperCase() + b.slice(1)}</option>
            ))}
          </select>
        </div>

        {/* Account number */}
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

        {/* Year — Barclays only */}
        {bank === "barclays" && (
          <div>
            <label className="text-xs text-gray-400">Statement year</label>
            <input
              type="number"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              className="mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">
              Auto-detected from filename/PDF when possible.
            </p>
          </div>
        )}

        {error && <p className="text-sm text-red-400">{error}</p>}
        {result && (
          <p className="text-sm text-green-400">
            Imported {result.added} transactions ({result.skipped} duplicates skipped).
          </p>
        )}

        <button
          type="submit"
          disabled={uploading || !file || !accountNumber}
          className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors"
        >
          {uploading ? "Uploading…" : "Upload & import"}
        </button>
      </form>
    </div>
  );
}

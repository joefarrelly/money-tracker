import { useEffect, useState } from "react";
import { getAccounts, updateAccount, getNiNumbers, setNiName } from "../api/client";
import type { Account } from "../types";

type NiRow = { ni_number: string; display_name: string | null; identity_id: number | null };

function EditableRow({
  label,
  sublabel,
  value,
  onSave,
  onDelete,
}: {
  label: string;
  sublabel?: string;
  value: string;
  onSave: (val: string) => Promise<void>;
  onDelete?: () => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!draft.trim()) return;
    setSaving(true);
    try {
      await onSave(draft.trim());
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  const cancel = () => { setDraft(value); setEditing(false); };

  return (
    <tr className="border-b border-slate-800/50 hover:bg-slate-800/30">
      <td className="px-4 py-3">
        <span className="text-sm font-mono text-slate-300">{label}</span>
        {sublabel && <span className="ml-2 text-xs text-slate-600">{sublabel}</span>}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <input
            value={editing ? draft : (value || "")}
            readOnly={!editing}
            autoFocus={editing || undefined}
            onChange={(e) => editing && setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") save();
              if (e.key === "Escape") cancel();
            }}
            placeholder={!editing ? "—" : undefined}
            className={
              editing
                ? "bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm w-48 text-slate-100"
                : "bg-transparent border-transparent text-sm text-slate-200 w-48 cursor-default placeholder-gray-600 focus:outline-none"
            }
          />
          {editing ? (
            <>
              <button
                onClick={save}
                disabled={saving}
                className="text-xs bg-green-700 hover:bg-green-600 disabled:opacity-50 px-2 py-1 rounded"
              >
                {saving ? "…" : "Save"}
              </button>
              <button onClick={cancel} className="text-xs text-slate-500 hover:text-slate-300">
                Cancel
              </button>
            </>
          ) : (
            <button
              onClick={() => { setDraft(value); setEditing(true); }}
              className="text-xs text-slate-600 hover:text-slate-300"
            >
              Edit
            </button>
          )}
        </div>
      </td>
      {onDelete && (
        <td className="px-4 py-3">
          <button onClick={onDelete} className="text-xs text-slate-600 hover:text-red-400">
            Delete
          </button>
        </td>
      )}
    </tr>
  );
}

export default function Settings() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [niRows, setNiRows] = useState<NiRow[]>([]);

  useEffect(() => {
    getAccounts().then(setAccounts);
    getNiNumbers().then(setNiRows);
  }, []);

  const handleSaveAccount = async (account: Account, nickname: string) => {
    const updated = await updateAccount(account.id, nickname);
    setAccounts((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
  };

  const handleSaveNiName = async (ni_number: string, display_name: string) => {
    const updated = await setNiName(ni_number, display_name);
    setNiRows((prev) =>
      prev.map((r) =>
        r.ni_number === ni_number
          ? { ...r, display_name: updated.display_name, identity_id: updated.id }
          : r
      )
    );
  };

  return (
    <div className="space-y-8">
      <h1 className="text-lg font-semibold">Settings</h1>

      {/* NI number names */}
      <section className="space-y-4">
        <div>
          <h2 className="text-sm font-medium text-slate-300">NI number names</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Assign a name to each NI number seen in your payslips.
          </p>
        </div>

        <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-slate-400">
                <th className="px-4 py-3">NI number</th>
                <th className="px-4 py-3">Name</th>
              </tr>
            </thead>
            <tbody>
              {niRows.map((row) => (
                <EditableRow
                  key={row.ni_number}
                  label={row.ni_number}
                  value={row.display_name ?? ""}
                  onSave={(val) => handleSaveNiName(row.ni_number, val)}
                />
              ))}
              {niRows.length === 0 && (
                <tr>
                  <td colSpan={2} className="px-4 py-6 text-slate-600 text-sm text-center">
                    No payslips imported yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Account nicknames */}
      <section className="space-y-4">
        <div>
          <h2 className="text-sm font-medium text-slate-300">Account nicknames</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Give your bank accounts a friendly name shown across the app.
          </p>
        </div>

        <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-slate-400">
                <th className="px-4 py-3">Account number</th>
                <th className="px-4 py-3">Nickname</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((account) => (
                <EditableRow
                  key={account.id}
                  label={account.account_number}
                  sublabel={account.bank}
                  value={account.nickname ?? ""}
                  onSave={(val) => handleSaveAccount(account, val)}
                />
              ))}
              {accounts.length === 0 && (
                <tr>
                  <td colSpan={2} className="px-4 py-6 text-slate-600 text-sm text-center">
                    No accounts yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

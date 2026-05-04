import { useEffect, useState } from "react";
import { Spinner } from "../components/Spinner";
import {
  getTransferCandidates,
  getConfirmedTransfers,
  confirmTransfer,
  ignoreTransfer,
  unlinkTransfer,
} from "../api/client";
import type { TransferCandidate, ConfirmedTransfer, TransferTxn } from "../types";

const fmt = (v: number) =>
  "£" + Math.abs(v).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function TxnCell({ t, side }: { t: TransferTxn; side: "out" | "in" }) {
  return (
    <div className={`flex-1 rounded-lg p-3 ${side === "out" ? "bg-red-950/30 border border-red-900/40" : "bg-green-950/30 border border-green-900/40"}`}>
      <div className="flex items-center justify-between mb-1">
        <span className={`text-sm font-semibold ${side === "out" ? "text-red-400" : "text-green-400"}`}>
          {side === "out" ? "−" : "+"}{fmt(t.amount)}
        </span>
        <span className="text-xs text-slate-500">{t.date}</span>
      </div>
      <p className="text-xs text-slate-300 truncate">{t.description}</p>
      <p className="text-xs text-slate-500 mt-0.5">{t.account_name}</p>
    </div>
  );
}

export default function Transfers() {
  const [candidates, setCandidates] = useState<TransferCandidate[]>([]);
  const [confirmed, setConfirmed] = useState<ConfirmedTransfer[]>([]);
  const [detecting, setDetecting] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = () =>
    Promise.all([getTransferCandidates(), getConfirmedTransfers()]).then(([c, cf]) => {
      setCandidates(c);
      setConfirmed(cf);
    });

  useEffect(() => {
    setLoading(true);
    load().finally(() => setLoading(false));
  }, []);

  const handleDetect = async () => {
    setDetecting(true);
    try {
      await load();
    } finally {
      setDetecting(false);
    }
  };

  const handleConfirm = async (c: TransferCandidate) => {
    await confirmTransfer(c.txn_out.id, c.txn_in.id);
    await load();
  };

  const handleIgnore = async (c: TransferCandidate) => {
    // Ignore the outgoing transaction so it won't resurface as a candidate
    await ignoreTransfer(c.txn_out.id);
    await load();
  };

  const handleUnlink = async (primaryId: number) => {
    await unlinkTransfer(primaryId);
    await load();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Transfers</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Internal account-to-account movements excluded from spending totals
          </p>
        </div>
        <button
          onClick={handleDetect}
          disabled={detecting}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          {detecting ? "Detecting…" : "Auto-detect transfers"}
        </button>
      </div>

      {loading && <Spinner />}

      {/* Candidates */}
      {!loading && (
        <section>
          <h2 className="text-sm font-medium text-slate-300 mb-3">
            Candidates
            {candidates.length > 0 && (
              <span className="ml-2 text-xs text-yellow-400 bg-yellow-900/30 px-2 py-0.5 rounded-full">
                {candidates.length}
              </span>
            )}
          </h2>

          {candidates.length === 0 ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-6 text-center text-sm text-slate-500">
              No transfer candidates found. Click "Auto-detect" after uploading statements from multiple accounts.
            </div>
          ) : (
            <div className="space-y-3">
              {candidates.map((c) => (
                <div
                  key={`${c.txn_out.id}-${c.txn_in.id}`}
                  className="bg-slate-900 border border-slate-800 rounded-xl p-4"
                >
                  <div className="flex items-center gap-3">
                    <TxnCell t={c.txn_out} side="out" />
                    <div className="flex flex-col items-center gap-1 flex-shrink-0">
                      <span className="text-slate-500 text-lg">⇄</span>
                      {c.day_diff > 0 && (
                        <span className="text-xs text-slate-600">{c.day_diff}d apart</span>
                      )}
                    </div>
                    <TxnCell t={c.txn_in} side="in" />
                  </div>
                  <div className="flex items-center justify-between mt-3">
                    <ConfidenceBadge confidence={c.confidence} />
                    <div className="flex gap-3">
                      <button
                        onClick={() => handleIgnore(c)}
                        className="text-sm text-slate-500 hover:text-slate-300 transition-colors"
                      >
                        Not a transfer
                      </button>
                      <button
                        onClick={() => handleConfirm(c)}
                        className="text-sm bg-emerald-700 hover:bg-emerald-600 px-3 py-1 rounded-lg font-medium transition-colors"
                      >
                        Confirm transfer
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Confirmed */}
      {!loading && confirmed.length > 0 && (
        <section>
          <h2 className="text-sm font-medium text-slate-300 mb-3">
            Confirmed transfers
            <span className="ml-2 text-xs text-slate-500">({confirmed.length})</span>
          </h2>

          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs text-slate-500 uppercase tracking-wide">
                  <th className="px-4 py-3 text-left">Date</th>
                  <th className="px-4 py-3 text-left">From</th>
                  <th className="px-4 py-3 text-right">Amount</th>
                  <th className="px-4 py-3 text-left">To</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {confirmed.map((cf) => {
                  const date = cf.txn_out?.date ?? cf.txn_in?.date ?? "—";
                  const amount = cf.txn_out?.amount ?? cf.txn_in?.amount ?? 0;
                  const fromName = cf.txn_out?.account_name ?? "—";
                  const fromDesc = cf.txn_out?.description ?? "—";
                  const toName = cf.txn_in?.account_name ?? "External";
                  const toDesc = cf.txn_in?.description;

                  return (
                    <tr key={cf.primary_id} className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30">
                      <td className="px-4 py-3 text-slate-400 tabular-nums">{date}</td>
                      <td className="px-4 py-3">
                        <p className="text-slate-200 truncate max-w-[180px]">{fromDesc}</p>
                        <p className="text-xs text-slate-500">{fromName}</p>
                      </td>
                      <td className="px-4 py-3 text-right font-medium tabular-nums text-slate-300">
                        {fmt(amount)}
                      </td>
                      <td className="px-4 py-3">
                        {toDesc ? (
                          <>
                            <p className="text-slate-200 truncate max-w-[180px]">{toDesc}</p>
                            <p className="text-xs text-slate-500">{toName}</p>
                          </>
                        ) : (
                          <p className="text-slate-500 italic">{toName}</p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleUnlink(cf.primary_id)}
                          className="text-xs text-slate-600 hover:text-red-400 transition-colors"
                        >
                          Unlink
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color =
    pct >= 85 ? "text-emerald-400 bg-emerald-900/30" :
    pct >= 60 ? "text-yellow-400 bg-yellow-900/30" :
                "text-slate-400 bg-slate-800";
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full ${color}`}>
      {pct}% confidence
    </span>
  );
}

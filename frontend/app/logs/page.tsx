"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ScrollText, RefreshCw, AlertCircle, ShieldCheck } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { apiFetch } from "@/lib/api";

interface LogRow {
  id: string;
  user_id: string | null;
  action: string;
  details: string | null;
  created_at: string;
}

export default function LogsPage() {
  const [logs, setLogs] = useState<LogRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  function refresh() {
    setLoading(true);
    apiFetch<LogRow[]>("/logs")
      .then(setLogs)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col border-b border-white/10 pb-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <ScrollText size={22} className="text-accent-blue" /> System Audit Trail & Event Logs
          </h1>
          <button onClick={refresh} className="p-2 rounded-lg bg-base-800 border border-white/10 text-slate-300 hover:text-white text-xs flex items-center gap-1.5">
            <RefreshCw size={14} className={loading ? "animate-spin text-accent-blue" : ""} /> Refresh Logs
          </button>
        </div>
        <p className="text-slate-400 text-xs mt-0.5">
          Admin-only audit trail capturing all state-changing API operations, training submissions, and security configuration edits.
        </p>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-severity-critical/10 border border-severity-critical/20 text-severity-critical text-xs flex items-center gap-2">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {/* Logs Table */}
      <Card>
        {loading ? (
          <p className="text-xs text-slate-400 py-8 text-center flex items-center justify-center gap-2">
            <RefreshCw size={14} className="animate-spin text-accent-blue" /> Querying audit logs...
          </p>
        ) : logs.length === 0 ? (
          <p className="text-xs text-slate-400 py-8 text-center">No log entries recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-slate-400 border-b border-white/5">
                  <th className="pb-2.5 font-semibold">Timestamp</th>
                  <th className="pb-2.5 font-semibold">Action / Route</th>
                  <th className="pb-2.5 font-semibold">Details</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} className="border-b border-white/5 last:border-0 hover:bg-white/[0.02]">
                    <td className="py-2.5 text-slate-400 whitespace-nowrap font-mono">{new Date(log.created_at).toLocaleString()}</td>
                    <td className="py-2.5 text-white font-mono font-medium">{log.action}</td>
                    <td className="py-2.5 text-slate-400">{log.details ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </motion.div>
  );
}

"use client";

import { useEffect, useState } from "react";
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

  useEffect(() => {
    apiFetch<LogRow[]>("/logs").then(setLogs).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-white">Audit Logs</h1>
        <p className="text-slate-400 text-sm">Admin-only trail of significant platform actions.</p>
      </div>

      {error && <p className="text-severity-critical text-sm">{error}</p>}

      <Card>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-400 border-b border-white/5">
              <th className="pb-2 font-normal">Time</th>
              <th className="pb-2 font-normal">Action</th>
              <th className="pb-2 font-normal">Details</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id} className="border-b border-white/5 last:border-0">
                <td className="py-2 text-slate-300 whitespace-nowrap">{new Date(log.created_at).toLocaleString()}</td>
                <td className="py-2 text-white">{log.action}</td>
                <td className="py-2 text-slate-400">{log.details ?? "-"}</td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr><td colSpan={3} className="py-4 text-slate-400 text-center">No log entries yet.</td></tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

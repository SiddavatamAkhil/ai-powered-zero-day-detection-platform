"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { AreaChart, Area, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";
import { StatCard } from "@/components/ui/Card";
import { api, apiFetch, Dataset } from "@/lib/api";

interface ActivityBucket {
  time: string;
  count: number;
}

export default function DashboardPage() {
  const [datasets, setDatasets] = useState<Dataset[] | null>(null);
  const [activity, setActivity] = useState<ActivityBucket[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listDatasets().then(setDatasets).catch((e) => setError(e.message));
    apiFetch<{ buckets: ActivityBucket[] }>("/activity-summary?hours=24")
      .then((res) => setActivity(res.buckets))
      .catch(() => setActivity([])); // non-fatal — chart just renders empty
  }, []);

  const totalRows = datasets?.reduce((sum, d) => sum + (d.num_rows ?? 0), 0) ?? 0;
  const totalUnknownClasses = datasets?.reduce(
    (sum, d) => sum + d.classes.filter((c) => c.split === "unknown_holdout").length,
    0
  ) ?? 0;

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-white">Overview</h1>
        <p className="text-slate-400 text-sm">Platform-wide status at a glance.</p>
      </div>

      {error && <p className="text-severity-critical text-sm">{error}</p>}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Datasets" value={datasets?.length ?? "-"} />
        <StatCard label="Total Samples" value={totalRows.toLocaleString()} />
        <StatCard label="Held-out Unknown Classes" value={totalUnknownClasses} />
        <StatCard label="Active Models" value="—" trend={{ value: "See Model Comparison", positive: true }} />
      </div>

      <div className="glass-card">
        <h2 className="text-white font-medium mb-4">Platform Activity (last 24h)</h2>
        {activity.length === 0 ? (
          <p className="text-slate-400 text-sm">
            No logged actions yet. Upload a dataset or start a training run — every state-changing
            request is recorded automatically and will appear here.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={activity}>
              <defs>
                <linearGradient id="detectionGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3B82F6" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#3B82F6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1B2740" />
              <XAxis dataKey="time" stroke="#64748B" fontSize={12} />
              <YAxis stroke="#64748B" fontSize={12} />
              <Tooltip contentStyle={{ background: "#0B1220", border: "1px solid #1B2740", borderRadius: 8 }} />
              <Area type="monotone" dataKey="count" stroke="#3B82F6" fill="url(#detectionGradient)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="glass-card">
        <h2 className="text-white font-medium mb-4">Datasets</h2>
        {!datasets ? (
          <p className="text-slate-400 text-sm">Loading...</p>
        ) : datasets.length === 0 ? (
          <p className="text-slate-400 text-sm">No datasets uploaded yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-400 border-b border-white/5">
                <th className="pb-2 font-normal">Name</th>
                <th className="pb-2 font-normal">Status</th>
                <th className="pb-2 font-normal">Rows</th>
                <th className="pb-2 font-normal">Classes (known / unknown)</th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr key={d.id} className="border-b border-white/5 last:border-0">
                  <td className="py-2 text-white">{d.name}</td>
                  <td className="py-2 text-slate-300">{d.status}</td>
                  <td className="py-2 text-slate-300">{d.num_rows ?? "-"}</td>
                  <td className="py-2">
                    <span className="badge-known mr-1">
                      {d.classes.filter((c) => c.split === "known").length} known
                    </span>
                    <span className="badge-unknown">
                      {d.classes.filter((c) => c.split === "unknown_holdout").length} unknown
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </motion.div>
  );
}

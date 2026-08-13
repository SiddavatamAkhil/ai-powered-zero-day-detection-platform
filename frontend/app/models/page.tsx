"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { Card } from "@/components/ui/Card";
import { api, MLModelResult, Dataset } from "@/lib/api";

export default function ModelsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("");
  const [models, setModels] = useState<MLModelResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listDatasets().then((ds) => {
      setDatasets(ds);
      if (ds.length > 0) setSelectedDatasetId(ds[0].id);
    }).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!selectedDatasetId) return;
    api.compareModels(selectedDatasetId).then(setModels).catch((e) => setError(e.message));
  }, [selectedDatasetId]);

  const chartData = models.map((m) => ({
    name: m.architecture,
    Accuracy: round(m.accuracy),
    F1: round(m.f1),
    "Unknown Recall": round(m.unknown_attack_recall),
  }));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Model Comparison</h1>
          <p className="text-slate-400 text-sm">Every architecture trained on the same known/unknown split.</p>
        </div>
        <select
          value={selectedDatasetId}
          onChange={(e) => setSelectedDatasetId(e.target.value)}
          className="bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
        >
          {datasets.map((d) => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>
      </div>

      {error && <p className="text-severity-critical text-sm">{error}</p>}

      <Card>
        <h2 className="text-white font-medium mb-4">Accuracy / F1 / Unknown-Attack Recall</h2>
        {models.length === 0 ? (
          <p className="text-slate-400 text-sm">No trained models yet for this dataset.</p>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1B2740" />
              <XAxis dataKey="name" stroke="#64748B" fontSize={12} />
              <YAxis stroke="#64748B" fontSize={12} domain={[0, 1]} />
              <Tooltip contentStyle={{ background: "#0B1220", border: "1px solid #1B2740", borderRadius: 8 }} />
              <Legend />
              <Bar dataKey="Accuracy" fill="#3B82F6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="F1" fill="#22D3EE" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Unknown Recall" fill="#8B5CF6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>

      <Card>
        <h2 className="text-white font-medium mb-4">Full Metrics</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm whitespace-nowrap">
            <thead>
              <tr className="text-left text-slate-400 border-b border-white/5">
                {["Model", "Accuracy", "Precision", "Recall", "F1", "MCC", "ROC-AUC", "FPR", "Unk. Recall", "Train (s)", "Infer (ms)"].map((h) => (
                  <th key={h} className="pb-2 pr-6 font-normal">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <tr key={m.id} className="border-b border-white/5 last:border-0">
                  <td className="py-2 pr-6 text-white">{m.architecture}</td>
                  <td className="py-2 pr-6 text-slate-300">{fmt(m.accuracy)}</td>
                  <td className="py-2 pr-6 text-slate-300">{fmt(m.precision)}</td>
                  <td className="py-2 pr-6 text-slate-300">{fmt(m.recall)}</td>
                  <td className="py-2 pr-6 text-slate-300">{fmt(m.f1)}</td>
                  <td className="py-2 pr-6 text-slate-300">{fmt(m.mcc)}</td>
                  <td className="py-2 pr-6 text-slate-300">{fmt(m.roc_auc)}</td>
                  <td className="py-2 pr-6 text-slate-300">{fmt(m.false_positive_rate)}</td>
                  <td className="py-2 pr-6 text-accent-cyan font-medium">{fmt(m.unknown_attack_recall)}</td>
                  <td className="py-2 pr-6 text-slate-300">{m.training_time_seconds?.toFixed(1) ?? "-"}</td>
                  <td className="py-2 pr-6 text-slate-300">{m.inference_time_ms_per_sample?.toFixed(2) ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function fmt(v: number | null) {
  return v === null || v === undefined ? "-" : v.toFixed(3);
}
function round(v: number | null) {
  return v === null || v === undefined ? 0 : Math.round(v * 1000) / 1000;
}

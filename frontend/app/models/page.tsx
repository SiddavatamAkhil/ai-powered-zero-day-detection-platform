"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { GitCompare, Sparkles, AlertCircle, RefreshCw, Layers } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { InfoPanel } from "@/components/ui/InfoPanel";
import { api, MLModelResult, Dataset } from "@/lib/api";

export default function ModelsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("");
  const [models, setModels] = useState<MLModelResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .listDatasets()
      .then((ds) => {
        setDatasets(ds);
        if (ds.length > 0) setSelectedDatasetId(ds[0].id);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedDatasetId) return;
    setLoading(true);
    api
      .compareModels(selectedDatasetId)
      .then(setModels)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [selectedDatasetId]);

  const chartData = models.map((m) => ({
    name: m.architecture.toUpperCase(),
    Accuracy: round(m.accuracy),
    F1: round(m.f1),
    "Zero-Day Recall": round(m.unknown_attack_recall),
  }));

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <GitCompare size={22} className="text-accent-blue" /> Model Benchmark & Comparison
          </h1>
          <p className="text-slate-400 text-xs mt-0.5">
            Compare evaluation metrics across trained deep learning architectures on identical known/unknown splits.
          </p>
        </div>

        <div>
          <select
            value={selectedDatasetId}
            onChange={(e) => setSelectedDatasetId(e.target.value)}
            className="bg-base-800 border border-white/10 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-accent-blue"
          >
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-severity-critical/10 border border-severity-critical/20 text-severity-critical text-xs flex items-center gap-2">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {/* Accuracy & Zero-Day Recall Chart */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white">Known Accuracy vs Zero-Day Recall Benchmark</h2>
          <span className="px-2.5 py-1 rounded bg-accent-blue/10 text-accent-blue text-xs font-mono border border-accent-blue/20">
            OpenMax EVT Metrics
          </span>
        </div>

        {loading ? (
          <p className="text-xs text-slate-400 py-8 text-center flex items-center justify-center gap-2">
            <RefreshCw size={14} className="animate-spin text-accent-blue" /> Comparing trained models...
          </p>
        ) : models.length === 0 ? (
          <p className="text-xs text-slate-400 py-8 text-center">No trained models found for this dataset yet. Train a model on the Training page.</p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1B2740" />
              <XAxis dataKey="name" stroke="#64748B" fontSize={11} />
              <YAxis stroke="#64748B" fontSize={11} domain={[0, 1]} />
              <Tooltip contentStyle={{ background: "#0B1220", border: "1px solid #1B2740", borderRadius: 8, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="Accuracy" fill="#3B82F6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="F1" fill="#22D3EE" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Zero-Day Recall" fill="#8B5CF6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>

      {/* Full Metrics Table */}
      <Card>
        <h2 className="text-sm font-semibold text-white mb-4">Full Benchmark Telemetry</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-xs whitespace-nowrap">
            <thead>
              <tr className="text-left text-slate-400 border-b border-white/5">
                {["Architecture", "Accuracy", "Precision", "Recall", "F1 Score", "MCC", "ROC-AUC", "FPR", "Zero-Day Recall", "Train (s)", "Infer (ms)"].map((h) => (
                  <th key={h} className="pb-2.5 pr-6 font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <tr key={m.id} className="border-b border-white/5 last:border-0 hover:bg-white/[0.02]">
                  <td className="py-3 pr-6 text-white font-semibold uppercase">{m.architecture}</td>
                  <td className="py-3 pr-6 text-slate-300">{fmt(m.accuracy)}</td>
                  <td className="py-3 pr-6 text-slate-300">{fmt(m.precision)}</td>
                  <td className="py-3 pr-6 text-slate-300">{fmt(m.recall)}</td>
                  <td className="py-3 pr-6 text-slate-300">{fmt(m.f1)}</td>
                  <td className="py-3 pr-6 text-slate-300">{fmt(m.mcc)}</td>
                  <td className="py-3 pr-6 text-slate-300">{fmt(m.roc_auc)}</td>
                  <td className="py-3 pr-6 text-slate-300">{fmt(m.false_positive_rate)}</td>
                  <td className="py-3 pr-6 text-accent-cyan font-bold bg-accent-cyan/10 px-2 py-1 rounded border border-accent-cyan/20">{fmt(m.unknown_attack_recall)}</td>
                  <td className="py-3 pr-6 text-slate-300">{m.training_time_seconds?.toFixed(1) ?? "-"}</td>
                  <td className="py-3 pr-6 text-slate-300">{m.inference_time_ms_per_sample?.toFixed(2) ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Contextual Educational Info Panel */}
      <InfoPanel
        title="Key Evaluation Metrics Explained"
        description="Understanding how zero-day platform evaluation differs from standard closed-set classifiers."
        bullets={[
          "Zero-Day Recall: Percentage of holdout unknown attack samples correctly rejected by OpenMax.",
          "Matthews Correlation Coefficient (MCC): Robust metric evaluating imbalanced attack class distributions.",
          "False Positive Rate (FPR): Frequency of benign traffic incorrectly flagged as threats.",
        ]}
      />
    </motion.div>
  );
}

function fmt(v: number | null) {
  return v === null || v === undefined ? "-" : v.toFixed(3);
}
function round(v: number | null) {
  return v === null || v === undefined ? 0 : Math.round(v * 1000) / 1000;
}

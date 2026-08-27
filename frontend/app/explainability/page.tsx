"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { Brain, Sparkles, AlertCircle, RefreshCw, Layers, CheckCircle2, Zap } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { InfoPanel } from "@/components/ui/InfoPanel";
import { api, apiFetch, Dataset, MLModelResult } from "@/lib/api";

interface Contribution {
  feature_name: string;
  contribution: number;
}

const SAMPLE_PRESETS = [
  {
    name: "ICMP Flood Attack (DoS)",
    sample: "0.0, 215.0, 45076.0, 0.0, 120.0, 1.0, 0.0, 0.0",
    description: "High ICMP packet count triggering DoS classification",
  },
  {
    name: "Port Scanning Activity (Probe)",
    sample: "0.0, 1.0, 0.0, 0.0, 240.0, 0.0, 1.0, 0.0",
    description: "Rapid TCP syn scanning across multiple port ranges",
  },
  {
    name: "Standard Normal Web Traffic (Benign)",
    sample: "0.1, 162.0, 4528.0, 0.0, 2.0, 0.0, 1.0, 0.0",
    description: "Standard HTTP GET request flow pattern",
  },
];

export default function ExplainabilityPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [datasetId, setDatasetId] = useState("");
  const [models, setModels] = useState<MLModelResult[]>([]);
  const [modelId, setModelId] = useState("");
  const [method, setMethod] = useState<"shap" | "lime">("shap");
  const [sampleInput, setSampleInput] = useState(SAMPLE_PRESETS[0].sample);
  const [result, setResult] = useState<{ predicted_class: string; contributions: Contribution[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .listDatasets()
      .then((ds) => {
        setDatasets(ds);
        if (ds.length > 0) setDatasetId(ds[0].id);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!datasetId) return;
    api.compareModels(datasetId).then((ms) => {
      setModels(ms);
      if (ms.length > 0) setModelId(ms[0].id);
    });
  }, [datasetId]);

  async function handleExplain(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!modelId) return;

    setError(null);
    setResult(null);
    setBusy(true);
    try {
      const sample = sampleInput.split(",").map((v) => parseFloat(v.trim()));
      if (sample.some(Number.isNaN)) throw new Error("Sample must be a comma-separated list of numbers.");

      const res = await apiFetch<{ predicted_class: string; contributions: Contribution[] }>(
        "/explainability/explain",
        { method: "POST", body: JSON.stringify({ model_id: modelId, sample, method }) }
      );
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Explanation failed.");
    } finally {
      setBusy(false);
    }
  }

  const chartData = result?.contributions
    .slice()
    .sort((a, b) => a.contribution - b.contribution)
    .map((c) => ({ name: c.feature_name, value: c.contribution }));

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col border-b border-white/10 pb-4">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Brain size={22} className="text-accent-blue" /> Explainable AI (SHAP & LIME)
        </h1>
        <p className="text-slate-400 text-xs mt-0.5">
          Quantify individual network flow feature contributions to explain deep neural network detection decisions.
        </p>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-severity-critical/10 border border-severity-critical/20 text-severity-critical text-xs flex items-center gap-2">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {/* Preset Selector Card */}
      <Card>
        <div className="flex items-center gap-2 mb-3">
          <Sparkles size={16} className="text-accent-cyan" />
          <h2 className="text-sm font-semibold text-white">Select Sample Preset for Instant Demo</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {SAMPLE_PRESETS.map((preset) => (
            <button
              key={preset.name}
              onClick={() => setSampleInput(preset.sample)}
              className={`p-3 rounded-xl border text-left transition-all ${
                sampleInput === preset.sample
                  ? "bg-accent-blue/10 border-accent-blue/40 text-white shadow-glow"
                  : "bg-base-950/60 border-white/5 text-slate-300 hover:bg-white/5"
              }`}
            >
              <span className="text-xs font-semibold block">{preset.name}</span>
              <p className="text-[11px] text-slate-400 mt-1">{preset.description}</p>
            </button>
          ))}
        </div>
      </Card>

      {/* Explanation Options Form */}
      <Card>
        <form onSubmit={handleExplain} className="flex flex-col gap-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="stat-label block mb-1">Dataset</label>
              <select
                value={datasetId}
                onChange={(e) => setDatasetId(e.target.value)}
                className="w-full bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-accent-blue"
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="stat-label block mb-1">Target Model</label>
              <select
                value={modelId}
                onChange={(e) => setModelId(e.target.value)}
                className="w-full bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-accent-blue"
              >
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.architecture.toUpperCase()} (ID: {m.id.substring(0, 8)})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="stat-label block mb-1">Attribution Algorithm</label>
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value as "shap" | "lime")}
                className="w-full bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-accent-blue font-semibold"
              >
                <option value="shap">SHAP (SHapley Additive exPlanations)</option>
                <option value="lime">LIME (Local Interpretable Model-agnostic Explanations)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="stat-label block mb-1">Packet Feature Vector (Comma-separated floats)</label>
            <textarea
              required
              value={sampleInput}
              onChange={(e) => setSampleInput(e.target.value)}
              rows={2}
              className="w-full bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-accent-blue"
            />
          </div>

          <div className="flex justify-end">
            <button type="submit" disabled={busy || !modelId} className="btn-primary flex items-center gap-2 text-xs disabled:opacity-50">
              {busy ? <RefreshCw size={14} className="animate-spin" /> : <Zap size={14} />}
              <span>{busy ? "Computing SHAP Attributions..." : "Explain Prediction"}</span>
            </button>
          </div>
        </form>
      </Card>

      {/* Explanation Results Chart */}
      {result && (
        <Card>
          <div className="flex items-center justify-between mb-2">
            <div>
              <h2 className="text-sm font-semibold text-white">
                Predicted Class: <span className="text-accent-cyan font-bold uppercase">{result.predicted_class}</span>
              </h2>
              <p className="text-xs text-slate-400">
                Positive feature weights push prediction toward <strong className="text-white">{result.predicted_class}</strong>; negative weights push away.
              </p>
            </div>
            <span className="px-2.5 py-1 rounded bg-accent-blue/10 text-accent-blue text-xs font-semibold border border-accent-blue/20">
              {method.toUpperCase()} Attribution Matrix
            </span>
          </div>

          <ResponsiveContainer width="100%" height={Math.max(220, (chartData?.length ?? 0) * 32)}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 120, right: 30 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1B2740" />
              <XAxis type="number" stroke="#64748B" fontSize={11} />
              <YAxis type="category" dataKey="name" stroke="#64748B" fontSize={11} width={120} />
              <Tooltip contentStyle={{ background: "#0B1220", border: "1px solid #1B2740", borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {chartData?.map((entry, i) => (
                  <Cell key={i} fill={entry.value >= 0 ? "#3B82F6" : "#EF4444"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Contextual Educational Info Panel */}
      <InfoPanel
        title="Understanding SHAP & LIME in Cybersecurity SOCs"
        description="Black-box neural networks cannot be deployed in critical SOC infrastructure without auditability."
        bullets={[
          "SHAP uses game-theoretic Shapley values to measure exact feature impact.",
          "Identifies whether byte counts, duration, or protocol flags triggered the alert.",
          "Empowers security analysts to verify model rationale before blocking IP traffic.",
        ]}
      />
    </motion.div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { Card } from "@/components/ui/Card";
import { api, apiFetch, Dataset, MLModelResult } from "@/lib/api";

interface Contribution {
  feature_name: string;
  contribution: number;
}

export default function ExplainabilityPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [datasetId, setDatasetId] = useState("");
  const [models, setModels] = useState<MLModelResult[]>([]);
  const [modelId, setModelId] = useState("");
  const [method, setMethod] = useState<"shap" | "lime">("shap");
  const [sampleInput, setSampleInput] = useState("");
  const [result, setResult] = useState<{ predicted_class: string; contributions: Contribution[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.listDatasets().then((ds) => {
      setDatasets(ds);
      if (ds.length > 0) setDatasetId(ds[0].id);
    });
  }, []);

  useEffect(() => {
    if (!datasetId) return;
    api.compareModels(datasetId).then((ms) => {
      setModels(ms);
      if (ms.length > 0) setModelId(ms[0].id);
    });
  }, [datasetId]);

  async function handleExplain(e: React.FormEvent) {
    e.preventDefault();
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
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-white">Explainability</h1>
        <p className="text-slate-400 text-sm">
          SHAP and LIME feature attributions for a single prediction. Requires a model trained
          after background-data persistence was added — older models will return an error.
        </p>
      </div>

      {error && <p className="text-severity-critical text-sm">{error}</p>}

      <Card>
        <form onSubmit={handleExplain} className="flex flex-col gap-4 max-w-2xl">
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="stat-label block mb-1">Dataset</label>
              <select
                value={datasetId} onChange={(e) => setDatasetId(e.target.value)}
                className="w-full bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
              >
                {datasets.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>
            <div className="flex-1">
              <label className="stat-label block mb-1">Model</label>
              <select
                value={modelId} onChange={(e) => setModelId(e.target.value)}
                className="w-full bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
              >
                {models.map((m) => <option key={m.id} value={m.id}>{m.architecture}</option>)}
              </select>
            </div>
            <div className="flex-1">
              <label className="stat-label block mb-1">Method</label>
              <select
                value={method} onChange={(e) => setMethod(e.target.value as "shap" | "lime")}
                className="w-full bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
              >
                <option value="shap">SHAP</option>
                <option value="lime">LIME</option>
              </select>
            </div>
          </div>

          <div>
            <label className="stat-label block mb-1">Sample (comma-separated feature values, in training column order)</label>
            <textarea
              required
              value={sampleInput}
              onChange={(e) => setSampleInput(e.target.value)}
              rows={3}
              placeholder="0.42, -1.2, 3.05, 0.0, ..."
              className="w-full bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white font-mono"
            />
          </div>

          <button type="submit" disabled={busy} className="btn-primary w-fit disabled:opacity-50">
            {busy ? "Explaining..." : "Explain Prediction"}
          </button>
        </form>
      </Card>

      {result && (
        <Card>
          <h2 className="text-white font-medium mb-1">
            Predicted class: <span className="text-accent-cyan">{result.predicted_class}</span>
          </h2>
          <p className="text-slate-400 text-xs mb-4">
            Positive bars push the prediction toward this class; negative bars push away from it.
          </p>
          <ResponsiveContainer width="100%" height={Math.max(200, (chartData?.length ?? 0) * 30)}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 100 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1B2740" />
              <XAxis type="number" stroke="#64748B" fontSize={12} />
              <YAxis type="category" dataKey="name" stroke="#64748B" fontSize={12} width={100} />
              <Tooltip contentStyle={{ background: "#0B1220", border: "1px solid #1B2740", borderRadius: 8 }} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {chartData?.map((entry, i) => (
                  <Cell key={i} fill={entry.value >= 0 ? "#3B82F6" : "#EF4444"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { api, Dataset } from "@/lib/api";

const ARCHITECTURES = ["cnn", "bilstm", "cnn_bilstm", "transformer", "autoencoder", "vae", "isolation_forest"];

export default function TrainingPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [datasetId, setDatasetId] = useState("");
  const [architecture, setArchitecture] = useState(ARCHITECTURES[0]);
  const [epochs, setEpochs] = useState(20);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listDatasets().then((ds) => {
      setDatasets(ds);
      if (ds.length > 0) setDatasetId(ds[0].id);
    });
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setStatus(null);
    try {
      const run: any = await api.startTraining({ dataset_id: datasetId, architecture, epochs });
      setStatus(`Training run queued (id: ${run.id}). Poll GET /training/runs/${run.id} for progress.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start training.");
    }
  }

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <div>
        <h1 className="text-xl font-semibold text-white">Training</h1>
        <p className="text-slate-400 text-sm">Train a new model on the known-class split of a dataset.</p>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="stat-label block mb-1">Dataset</label>
            <select
              value={datasetId}
              onChange={(e) => setDatasetId(e.target.value)}
              className="w-full bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            >
              {datasets.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </div>

          <div>
            <label className="stat-label block mb-1">Architecture</label>
            <select
              value={architecture}
              onChange={(e) => setArchitecture(e.target.value)}
              className="w-full bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            >
              {ARCHITECTURES.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>

          <div>
            <label className="stat-label block mb-1">Epochs</label>
            <input
              type="number"
              min={1}
              max={500}
              value={epochs}
              onChange={(e) => setEpochs(Number(e.target.value))}
              className="w-full bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            />
          </div>

          {error && <p className="text-severity-critical text-xs">{error}</p>}
          {status && <p className="text-severity-low text-xs">{status}</p>}

          <button type="submit" className="btn-primary w-fit">Start Training</button>
        </form>
      </Card>
    </div>
  );
}

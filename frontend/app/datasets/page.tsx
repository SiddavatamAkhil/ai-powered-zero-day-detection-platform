"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { api, apiFetch, Dataset } from "@/lib/api";

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selected, setSelected] = useState<Dataset | null>(null);
  const [name, setName] = useState("");
  const [labelColumn, setLabelColumn] = useState("label");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function refresh() {
    api.listDatasets().then(setDatasets).catch((e) => setError(e.message));
  }

  useEffect(refresh, []);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("name", name);
      form.append("label_column", labelColumn);
      form.append("file", file);
      await apiFetch("/datasets/upload", { method: "POST", body: form });
      setName("");
      setFile(null);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  async function runStage(datasetId: string, stage: "profile" | "clean" | "feature-engineer") {
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/datasets/${datasetId}/${stage}`, { method: "POST" });
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : `${stage} failed.`);
    } finally {
      setBusy(false);
    }
  }

  async function toggleSplit(datasetId: string, className: string, current: string) {
    const next = current === "known" ? "unknown_holdout" : "known";
    setBusy(true);
    try {
      await apiFetch(`/datasets/${datasetId}/open-set-split`, {
        method: "POST",
        body: JSON.stringify({ assignments: [{ class_name: className, split: next }] }),
      });
      refresh();
      if (selected?.id === datasetId) {
        api.getDataset(datasetId).then(setSelected);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-white">Datasets</h1>
        <p className="text-slate-400 text-sm">Upload, clean, feature-engineer, and configure the known/unknown split.</p>
      </div>

      {error && <p className="text-severity-critical text-sm">{error}</p>}

      <Card>
        <h2 className="text-white font-medium mb-4">Upload New Dataset</h2>
        <form onSubmit={handleUpload} className="flex flex-col gap-4 max-w-lg">
          <div>
            <label className="stat-label block mb-1">Dataset Name</label>
            <input
              required value={name} onChange={(e) => setName(e.target.value)}
              className="w-full bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            />
          </div>
          <div>
            <label className="stat-label block mb-1">Label Column</label>
            <input
              required value={labelColumn} onChange={(e) => setLabelColumn(e.target.value)}
              className="w-full bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            />
          </div>
          <div>
            <label className="stat-label block mb-1">CSV File</label>
            <input
              type="file" accept=".csv" required
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="w-full text-sm text-slate-300"
            />
          </div>
          <button type="submit" disabled={busy} className="btn-primary w-fit disabled:opacity-50">
            {busy ? "Working..." : "Upload"}
          </button>
        </form>
      </Card>

      <Card>
        <h2 className="text-white font-medium mb-4">All Datasets</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-400 border-b border-white/5">
              <th className="pb-2 font-normal">Name</th>
              <th className="pb-2 font-normal">Status</th>
              <th className="pb-2 font-normal">Rows</th>
              <th className="pb-2 font-normal">Actions</th>
            </tr>
          </thead>
          <tbody>
            {datasets.map((d) => (
              <tr key={d.id} className="border-b border-white/5 last:border-0">
                <td className="py-2 text-white">
                  <button className="hover:text-accent-blue" onClick={() => setSelected(d)}>{d.name}</button>
                </td>
                <td className="py-2 text-slate-300">{d.status}</td>
                <td className="py-2 text-slate-300">{d.num_rows ?? "-"}</td>
                <td className="py-2 flex gap-2">
                  <button onClick={() => runStage(d.id, "profile")} className="text-xs text-accent-cyan hover:underline">Profile</button>
                  <button onClick={() => runStage(d.id, "clean")} className="text-xs text-accent-cyan hover:underline">Clean</button>
                  <button onClick={() => runStage(d.id, "feature-engineer")} className="text-xs text-accent-cyan hover:underline">Feature Engineer</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {selected && (
        <Card>
          <h2 className="text-white font-medium mb-4">Open-Set Split — {selected.name}</h2>
          <p className="text-slate-400 text-xs mb-4">
            Toggle a class to Unknown to hold it out entirely from training, simulating a zero-day attack.
            Benign traffic cannot be held out.
          </p>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-400 border-b border-white/5">
                <th className="pb-2 font-normal">Class</th>
                <th className="pb-2 font-normal">Samples</th>
                <th className="pb-2 font-normal">Split</th>
              </tr>
            </thead>
            <tbody>
              {selected.classes.map((c) => (
                <tr key={c.class_name} className="border-b border-white/5 last:border-0">
                  <td className="py-2 text-white">{c.class_name}</td>
                  <td className="py-2 text-slate-300">{c.sample_count}</td>
                  <td className="py-2">
                    <button
                      disabled={c.is_benign || busy}
                      onClick={() => toggleSplit(selected.id, c.class_name, c.split)}
                      className={c.split === "known" ? "badge-known" : "badge-unknown"}
                    >
                      {c.split === "known" ? "Known" : "Unknown"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

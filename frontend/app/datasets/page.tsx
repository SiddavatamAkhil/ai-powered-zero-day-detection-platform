"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Database, FileUp, Sparkles, AlertCircle, RefreshCw, CheckCircle2, Sliders, Layers, Trash2 } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { InfoPanel } from "@/components/ui/InfoPanel";
import { StepProgressLoader, ProgressStage } from "@/components/ui/StepProgressLoader";
import { api, apiFetch, Dataset } from "@/lib/api";
import { useDemo } from "@/components/DemoContext";

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selected, setSelected] = useState<Dataset | null>(null);
  const [name, setName] = useState("");
  const [labelColumn, setLabelColumn] = useState("label");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);

  // Multi-stage progress state for processing
  const [activeStageTitle, setActiveStageTitle] = useState<string | null>(null);
  const [progressStages, setProgressStages] = useState<ProgressStage[]>([]);

  const { active: isDemoActive, nextStep } = useDemo();

  function refresh() {
    setLoading(true);
    api
      .listDatasets()
      .then((ds) => {
        setDatasets(ds);
        if (ds.length > 0 && !selected) setSelected(ds[0]);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
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

  async function handleDelete(datasetId: string) {
    if (!confirm("Delete this dataset? This cannot be undone.")) return;
    setBusy(true);
    setError(null);
    try {
      await api.deleteDataset(datasetId);
      if (selected?.id === datasetId) setSelected(null);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed.");
    } finally {
      setBusy(false);
    }
  }

  const demoAlreadyExists = datasets.some((d) => d.name === "NSL-KDD Demo Flow Matrix");

  // Load Demo Dataset feature
  async function handleLoadDemoDataset() {
    if (demoAlreadyExists) {
      setError("Demo dataset already exists. Delete it first before reloading.");
      return;
    }
    setDemoLoading(true);
    setError(null);
    try {
      const demoCsvContent = `duration,src_bytes,dst_bytes,wrong_fragment,count,protocol_type_icmp,protocol_type_tcp,protocol_type_udp,label
0.0,215.0,45076.0,0.0,1.0,0.0,1.0,0.0,benign
0.0,162.0,4528.0,0.0,2.0,0.0,1.0,0.0,benign
0.0,230.0,1280.0,0.0,1.0,0.0,1.0,0.0,benign
0.0,180.0,900.0,0.0,1.0,0.0,1.0,0.0,benign
0.0,190.0,1100.0,0.0,1.0,0.0,1.0,0.0,benign
0.0,200.0,1500.0,0.0,1.0,0.0,1.0,0.0,benign
0.0,210.0,1400.0,0.0,1.0,0.0,1.0,0.0,benign
0.0,220.0,1600.0,0.0,1.0,0.0,1.0,0.0,benign
0.0,0.0,0.0,0.0,120.0,0.0,1.0,0.0,dos
0.0,0.0,0.0,0.0,240.0,0.0,1.0,0.0,dos
0.0,0.0,0.0,0.0,180.0,0.0,1.0,0.0,dos
0.0,0.0,0.0,0.0,300.0,0.0,1.0,0.0,dos
0.0,0.0,0.0,0.0,150.0,0.0,1.0,0.0,dos
0.0,0.0,0.0,0.0,200.0,0.0,1.0,0.0,dos
0.0,0.0,0.0,0.0,220.0,0.0,1.0,0.0,dos
0.0,0.0,0.0,0.0,250.0,0.0,1.0,0.0,dos
0.0,1.0,0.0,0.0,1.0,1.0,0.0,0.0,probe
0.0,1.0,0.0,0.0,2.0,1.0,0.0,0.0,probe
0.0,1.0,0.0,0.0,3.0,1.0,0.0,0.0,probe
0.0,1.0,0.0,0.0,4.0,1.0,0.0,0.0,probe
0.0,1.0,0.0,0.0,5.0,1.0,0.0,0.0,probe
0.0,1.0,0.0,0.0,6.0,1.0,0.0,0.0,probe
0.1,10.0,0.0,0.0,1.0,0.0,1.0,0.0,r2l
0.1,12.0,0.0,0.0,1.0,0.0,1.0,0.0,r2l
0.1,14.0,0.0,0.0,1.0,0.0,1.0,0.0,r2l
0.1,16.0,0.0,0.0,1.0,0.0,1.0,0.0,r2l
0.2,50.0,100.0,0.0,1.0,0.0,1.0,0.0,u2r
0.2,60.0,120.0,0.0,1.0,0.0,1.0,0.0,u2r
0.2,70.0,140.0,0.0,1.0,0.0,1.0,0.0,u2r
0.2,80.0,160.0,0.0,1.0,0.0,1.0,0.0,u2r
`;
      const blob = new Blob([demoCsvContent], { type: "text/csv" });
      const demoFile = new File([blob], "demo_nsl_kdd_subset.csv", { type: "text/csv" });

      const form = new FormData();
      form.append("name", "NSL-KDD Demo Flow Matrix");
      form.append("label_column", "label");
      form.append("file", demoFile);

      const createdDs = await apiFetch<Dataset>("/datasets/upload", { method: "POST", body: form });

      // Auto-run the full pipeline so the dataset is immediately ready to train
      const id = createdDs.id;
      await apiFetch(`/datasets/${id}/profile`, { method: "POST" });
      await apiFetch(`/datasets/${id}/clean`, { method: "POST" });
      await apiFetch(`/datasets/${id}/feature-engineer`, { method: "POST" });
      await apiFetch(`/datasets/${id}/open-set-split`, {
        method: "POST",
        body: JSON.stringify({
          assignments: [
            { class_name: "benign", split: "known" },
            { class_name: "dos", split: "known" },
            { class_name: "probe", split: "known" },
            { class_name: "r2l", split: "known" },
            { class_name: "u2r", split: "known" },
          ],
        }),
      });

      refresh();
      const ready = await api.getDataset(id);
      setSelected(ready);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load demo dataset.");
    } finally {
      setDemoLoading(false);
    }
  }

  async function runStage(datasetId: string, stage: "profile" | "clean" | "feature-engineer") {
    setBusy(true);
    setError(null);

    const stageTitles = {
      profile: "Profiling Raw Dataset",
      clean: "Cleaning & Missing Value Removal",
      "feature-engineer": "Feature Engineering (PyArrow Parquet)",
    };

    setActiveStageTitle(stageTitles[stage]);
    setProgressStages([
      { id: "1", label: "Validating CSV Structure", status: "completed" },
      { id: "2", label: `Executing ${stage} Pipeline`, status: "active" },
      { id: "3", label: "Persisting Metadata & Arrays", status: "pending" },
    ]);

    try {
      await apiFetch(`/datasets/${datasetId}/${stage}`, { method: "POST" });
      setProgressStages([
        { id: "1", label: "Validating CSV Structure", status: "completed" },
        { id: "2", label: `Executing ${stage} Pipeline`, status: "completed" },
        { id: "3", label: "Persisting Metadata & Arrays", status: "completed" },
      ]);
      refresh();
      const updatedDs = await api.getDataset(datasetId);
      setSelected(updatedDs);
    } catch (err) {
      setProgressStages((prev) =>
        prev.map((s) => (s.status === "active" ? { ...s, status: "failed", detail: err instanceof Error ? err.message : "Stage failed." } : s))
      );
      setError(err instanceof Error ? err.message : `${stage} failed.`);
    } finally {
      setTimeout(() => {
        setBusy(false);
        setActiveStageTitle(null);
      }, 1200);
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
      const updated = await api.getDataset(datasetId);
      setSelected(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to toggle split.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Database size={22} className="text-accent-blue" /> Datasets & Open-Set Splits
          </h1>
          <p className="text-slate-400 text-xs mt-0.5">
            Ingest raw network traffic CSVs, clean features into Parquet binary arrays, and configure known vs unknown zero-day splits.
          </p>
        </div>

        {/* Demo Support Option */}
        <button
          onClick={handleLoadDemoDataset}
          disabled={demoLoading || busy || demoAlreadyExists}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-accent-blue/10 text-accent-blue text-xs font-semibold border border-accent-blue/20 hover:bg-accent-blue/20 transition-all disabled:opacity-50"
        >
          {demoLoading ? <RefreshCw size={14} className="animate-spin" /> : <Sparkles size={14} />}
          <span>{demoLoading ? "Preparing Demo..." : "Load Demo Dataset"}</span>
        </button>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-severity-critical/10 border border-severity-critical/20 text-severity-critical text-xs flex items-center gap-2">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {/* Active Pipeline Multi-Stage Progress Loader */}
      {activeStageTitle && (
        <StepProgressLoader
          title={activeStageTitle}
          stages={progressStages}
          onRetry={() => refresh()}
        />
      )}

      {/* Upload Form Card */}
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <FileUp size={18} className="text-accent-cyan" />
          <h2 className="text-sm font-semibold text-white">Upload New Traffic Dataset</h2>
        </div>

        <form onSubmit={handleUpload} className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="stat-label block mb-1">Dataset Name</label>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. CIC-IDS-2024 Traffic"
              className="w-full bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-accent-blue"
            />
          </div>

          <div>
            <label className="stat-label block mb-1">Label Column Name</label>
            <input
              required
              value={labelColumn}
              onChange={(e) => setLabelColumn(e.target.value)}
              placeholder="e.g. label"
              className="w-full bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-accent-blue"
            />
          </div>

          <div>
            <label className="stat-label block mb-1">CSV File</label>
            <input
              type="file"
              accept=".csv"
              required
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="w-full text-xs text-slate-300 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-base-700 file:text-white hover:file:bg-base-600 cursor-pointer"
            />
          </div>

          <div className="md:col-span-3 flex justify-end">
            <button type="submit" disabled={busy || !file} className="btn-primary flex items-center gap-2 text-xs disabled:opacity-50">
              {busy ? <RefreshCw size={14} className="animate-spin" /> : <FileUp size={14} />}
              <span>Upload CSV</span>
            </button>
          </div>
        </form>
      </Card>

      {/* Datasets Table */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <Layers size={16} className="text-accent-blue" /> Indexed Datasets
          </h2>
          <span className="text-xs text-slate-400">{datasets.length} datasets uploaded</span>
        </div>

        {loading ? (
          <p className="text-xs text-slate-400 py-4 flex items-center gap-2">
            <RefreshCw size={14} className="animate-spin text-accent-blue" /> Loading datasets...
          </p>
        ) : datasets.length === 0 ? (
          <div className="p-8 text-center border border-dashed border-white/10 rounded-xl">
            <p className="text-xs text-slate-400 mb-3">No datasets uploaded yet.</p>
            <button onClick={handleLoadDemoDataset} className="btn-primary text-xs flex items-center gap-1.5 mx-auto">
              <Sparkles size={14} /> Click here to load sample demo dataset
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-slate-400 border-b border-white/5">
                  <th className="pb-2.5 font-semibold">Name</th>
                  <th className="pb-2.5 font-semibold">Status</th>
                  <th className="pb-2.5 font-semibold">Rows</th>
                  <th className="pb-2.5 font-semibold">Classes (Known / Unknown)</th>
                  <th className="pb-2.5 font-semibold text-right">Pipeline Actions</th>
                  <th className="pb-2.5 font-semibold text-right"></th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((d) => (
                  <tr key={d.id} className="border-b border-white/5 last:border-0 hover:bg-white/[0.02]">
                    <td className="py-3 text-white font-medium">
                      <button
                        className="hover:text-accent-cyan transition-colors text-left flex items-center gap-2"
                        onClick={() => setSelected(d)}
                      >
                        {d.name}
                        {selected?.id === d.id && <span className="h-1.5 w-1.5 rounded-full bg-accent-cyan" />}
                      </button>
                    </td>
                    <td className="py-3 text-slate-300">
                      <span className="px-2 py-0.5 rounded text-[10px] bg-base-800 border border-white/10 font-mono">
                        {d.status}
                      </span>
                    </td>
                    <td className="py-3 text-slate-300">{d.num_rows ? d.num_rows.toLocaleString() : "-"}</td>
                    <td className="py-3">
                      <span className="badge-known mr-1.5">
                        {d.classes.filter((c) => c.split === "known").length} Known
                      </span>
                      <span className="badge-unknown">
                        {d.classes.filter((c) => c.split === "unknown_holdout").length} Unknown Zero-Day
                      </span>
                    </td>
                    <td className="py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => runStage(d.id, "profile")}
                          disabled={busy}
                          className="px-2.5 py-1 rounded bg-base-800 text-[11px] text-accent-cyan hover:bg-base-700 border border-white/10 transition-colors"
                        >
                          Profile
                        </button>
                        <button
                          onClick={() => runStage(d.id, "clean")}
                          disabled={busy}
                          className="px-2.5 py-1 rounded bg-base-800 text-[11px] text-accent-cyan hover:bg-base-700 border border-white/10 transition-colors"
                        >
                          Clean
                        </button>
                        <button
                          onClick={() => runStage(d.id, "feature-engineer")}
                          disabled={busy}
                          className="px-2.5 py-1 rounded bg-base-800 text-[11px] text-accent-cyan hover:bg-base-700 border border-white/10 transition-colors"
                        >
                          Engineer Matrix
                        </button>
                      </div>
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => handleDelete(d.id)}
                        disabled={busy}
                        title="Delete dataset"
                        className="p-1.5 rounded hover:bg-severity-critical/20 text-slate-500 hover:text-severity-critical border border-transparent hover:border-severity-critical/30 transition-colors disabled:opacity-30"
                      >
                        <Trash2 size={13} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Selected Open-Set Split Configuration */}
      {selected && (
        <Card>
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              <Sliders size={16} className="text-accent-cyan" /> Open-Set Zero-Day Class Split — {selected.name}
            </h2>
          </div>
          <p className="text-xs text-slate-400 mb-4">
            Toggle an attack class to <strong className="text-severity-critical">Unknown (Zero-Day Holdout)</strong> to exclude it entirely from training.
            This simulates an un-signacured zero-day exploit to benchmark OpenMax detection recall.
          </p>

          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-slate-400 border-b border-white/5">
                  <th className="pb-2 font-semibold">Class Name</th>
                  <th className="pb-2 font-semibold">Sample Count</th>
                  <th className="pb-2 font-semibold">Allocation Status</th>
                  <th className="pb-2 font-semibold text-right">Toggle Split</th>
                </tr>
              </thead>
              <tbody>
                {selected.classes.map((c) => (
                  <tr key={c.class_name} className="border-b border-white/5 last:border-0">
                    <td className="py-2.5 text-white font-medium flex items-center gap-2">
                      <span className={c.is_benign ? "text-severity-low font-semibold" : "text-white"}>
                        {c.class_name}
                      </span>
                      {c.is_benign && (
                        <span className="text-[10px] bg-severity-low/10 text-severity-low px-1.5 py-0.2 rounded border border-severity-low/20">
                          Benign Traffic
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 text-slate-300">{c.sample_count.toLocaleString()}</td>
                    <td className="py-2.5">
                      <span className={c.split === "known" ? "badge-known" : "badge-unknown"}>
                        {c.split === "known" ? "Known (In Train Set)" : "Unknown (Held-Out Zero-Day)"}
                      </span>
                    </td>
                    <td className="py-2.5 text-right">
                      <button
                        disabled={c.is_benign || busy}
                        onClick={() => toggleSplit(selected.id, c.class_name, c.split)}
                        className="px-3 py-1 rounded bg-base-800 text-xs font-medium text-slate-200 border border-white/10 hover:bg-base-700 disabled:opacity-30 transition-colors"
                      >
                        Set to {c.split === "known" ? "Unknown" : "Known"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Contextual Educational Info Panel */}
      <InfoPanel
        title="Why Open-Set Splits Matter for Evaluation"
        description="Traditional benchmarks train models on all attack classes, leading to inflated 99% accuracy rates that fail in real-world SOC deployments against novel exploits."
        bullets={[
          "Benign baseline traffic is kept in the known training set.",
          "Holdout attack classes are completely hidden during PyTorch model training.",
          "OpenMax EVT Weibull layer calculates distance thresholds to reject holdout samples.",
        ]}
      />
    </motion.div>
  );
}

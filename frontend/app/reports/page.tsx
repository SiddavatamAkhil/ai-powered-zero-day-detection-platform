"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { FileDown, RefreshCw, FileText, AlertCircle, CheckCircle2 } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { InfoPanel } from "@/components/ui/InfoPanel";
import { api, downloadBlob, Dataset } from "@/lib/api";

export default function ReportsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .listDatasets()
      .then(setDatasets)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function downloadReport(datasetId: string, datasetName: string) {
    setDownloadingId(datasetId);
    setError(null);
    try {
      const blob = await downloadBlob(`/reports/dataset/${datasetId}/pdf`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${datasetName.toLowerCase().replace(/\s+/g, "_")}_evaluation_report.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate or download PDF report.");
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col border-b border-white/10 pb-4">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <FileText size={22} className="text-accent-blue" /> Publication-Ready Executive PDF Reports
        </h1>
        <p className="text-slate-400 text-xs mt-0.5">
          Generate structured PDF evaluation reports compiling model benchmark comparisons, class distributions, and OpenMax zero-day detection statistics.
        </p>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-severity-critical/10 border border-severity-critical/20 text-severity-critical text-xs flex items-center gap-2">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {/* Reports Table */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white">Available Evaluation Reports</h2>
          <span className="text-xs text-slate-400">PDF Generator Engine: ReportLab 4.x</span>
        </div>

        {loading ? (
          <p className="text-xs text-slate-400 py-8 text-center flex items-center justify-center gap-2">
            <RefreshCw size={14} className="animate-spin text-accent-blue" /> Fetching available datasets...
          </p>
        ) : datasets.length === 0 ? (
          <p className="text-xs text-slate-400 py-8 text-center">No datasets uploaded yet. Upload a dataset to generate reports.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-slate-400 border-b border-white/5">
                  <th className="pb-2.5 font-semibold">Dataset Name</th>
                  <th className="pb-2.5 font-semibold">Ingestion Status</th>
                  <th className="pb-2.5 font-semibold">Sample Tally</th>
                  <th className="pb-2.5 font-semibold text-right">Report Export</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((d) => (
                  <tr key={d.id} className="border-b border-white/5 last:border-0 hover:bg-white/[0.02]">
                    <td className="py-3 text-white font-medium">{d.name}</td>
                    <td className="py-3 text-slate-300">
                      <span className="px-2 py-0.5 rounded text-[10px] bg-base-800 border border-white/10 font-mono">
                        {d.status}
                      </span>
                    </td>
                    <td className="py-3 text-slate-300">{d.num_rows ? d.num_rows.toLocaleString() : "-"} samples</td>
                    <td className="py-3 text-right">
                      <button
                        disabled={downloadingId === d.id}
                        onClick={() => downloadReport(d.id, d.name)}
                        className="btn-primary inline-flex items-center gap-1.5 text-xs disabled:opacity-50"
                      >
                        {downloadingId === d.id ? (
                          <>
                            <RefreshCw size={14} className="animate-spin" /> Compiling PDF...
                          </>
                        ) : (
                          <>
                            <FileDown size={14} /> Export PDF Report
                          </>
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Contextual Educational Info Panel */}
      <InfoPanel
        title="What is Included in the PDF Report?"
        description="The report generator builds a formal PDF document designed for academic defenses and enterprise SOC audits."
        bullets={[
          "Executive summary of total dataset samples & open-set splits.",
          "Comparative metric tables (Accuracy, F1, MCC, FPR, Zero-Day Recall).",
          "OpenMax Weibull tail parameters and EVT thresholding curve.",
        ]}
      />
    </motion.div>
  );
}

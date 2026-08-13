"use client";

import { useEffect, useState } from "react";
import { FileDown } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { api, Dataset } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export default function ReportsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listDatasets().then(setDatasets).catch((e) => setError(e.message));
  }, []);

  function downloadReport(datasetId: string) {
    const tokens = JSON.parse(window.localStorage.getItem("zeroday_tokens") ?? "{}");
    fetch(`${API_URL}/reports/dataset/${datasetId}/pdf`, {
      headers: { Authorization: `Bearer ${tokens.access_token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error("No trained models yet for this dataset.");
        return res.blob();
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "evaluation_report.pdf";
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch((e) => setError(e.message));
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-white">Reports</h1>
        <p className="text-slate-400 text-sm">Generate a PDF evaluation report comparing all trained models for a dataset.</p>
      </div>

      {error && <p className="text-severity-critical text-sm">{error}</p>}

      <Card>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-400 border-b border-white/5">
              <th className="pb-2 font-normal">Dataset</th>
              <th className="pb-2 font-normal">Status</th>
              <th className="pb-2 font-normal"></th>
            </tr>
          </thead>
          <tbody>
            {datasets.map((d) => (
              <tr key={d.id} className="border-b border-white/5 last:border-0">
                <td className="py-2 text-white">{d.name}</td>
                <td className="py-2 text-slate-300">{d.status}</td>
                <td className="py-2">
                  <button
                    onClick={() => downloadReport(d.id)}
                    className="flex items-center gap-1 text-xs text-accent-cyan hover:underline"
                  >
                    <FileDown size={14} /> Download PDF
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

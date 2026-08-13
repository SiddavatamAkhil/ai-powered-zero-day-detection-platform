"use client";

import { useEffect, useRef, useState } from "react";
import { Wifi, WifiOff, ShieldAlert, ShieldCheck } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { api, MLModelResult, Dataset } from "@/lib/api";

interface DetectionEvent {
  timestamp: number;
  predicted_class: string;
  confidence: number;
  is_unknown: boolean;
}

const WS_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1")
  .replace("http://", "ws://")
  .replace("https://", "wss://");

export default function SimulationPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [datasetId, setDatasetId] = useState("");
  const [models, setModels] = useState<MLModelResult[]>([]);
  const [modelId, setModelId] = useState("");
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<DetectionEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

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

  function connect() {
    if (!modelId) return;
    const tokens = JSON.parse(window.localStorage.getItem("zeroday_tokens") ?? "{}");
    const ws = new WebSocket(`${WS_BASE}/simulation/ws/${modelId}?token=${tokens.access_token}`);

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setError("WebSocket connection failed.");
    ws.onmessage = (msg) => {
      const data = JSON.parse(msg.data);
      if (data.error) {
        setError(data.error);
        return;
      }
      setEvents((prev) => [data, ...prev].slice(0, 50));
    };

    wsRef.current = ws;
  }

  function disconnect() {
    wsRef.current?.close();
    wsRef.current = null;
  }

  useEffect(() => () => wsRef.current?.close(), []);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-white">Live Packet Simulation</h1>
        <p className="text-slate-400 text-sm">
          Streams synthetically generated flow records through a trained model in real time.
          This is a simulation, not a live network capture — it exercises the real trained model
          and OpenMax open-set logic against generated traffic, useful for demoing detection
          behavior without needing a live network tap.
        </p>
      </div>

      {error && <p className="text-severity-critical text-sm">{error}</p>}

      <Card>
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="stat-label block mb-1">Dataset</label>
            <select
              value={datasetId}
              onChange={(e) => setDatasetId(e.target.value)}
              className="bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            >
              {datasets.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </div>
          <div>
            <label className="stat-label block mb-1">Model</label>
            <select
              value={modelId}
              onChange={(e) => setModelId(e.target.value)}
              className="bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            >
              {models.map((m) => <option key={m.id} value={m.id}>{m.architecture}</option>)}
            </select>
          </div>
          {!connected ? (
            <button onClick={connect} className="btn-primary flex items-center gap-2">
              <Wifi size={16} /> Start Feed
            </button>
          ) : (
            <button onClick={disconnect} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-severity-critical/10 text-severity-critical text-sm border border-severity-critical/20">
              <WifiOff size={16} /> Stop Feed
            </button>
          )}
        </div>
      </Card>

      <Card>
        <h2 className="text-white font-medium mb-4">Detection Feed</h2>
        {events.length === 0 ? (
          <p className="text-slate-400 text-sm">No events yet. Start the feed above.</p>
        ) : (
          <div className="flex flex-col gap-2 max-h-96 overflow-y-auto">
            {events.map((e, i) => (
              <div key={i} className="flex items-center justify-between text-sm py-2 border-b border-white/5 last:border-0">
                <div className="flex items-center gap-2">
                  {e.is_unknown ? (
                    <ShieldAlert size={16} className="text-severity-critical" />
                  ) : (
                    <ShieldCheck size={16} className="text-severity-low" />
                  )}
                  <span className={e.is_unknown ? "text-severity-critical font-medium" : "text-white"}>
                    {e.predicted_class}
                  </span>
                </div>
                <span className="text-slate-400">{(e.confidence * 100).toFixed(1)}% confidence</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

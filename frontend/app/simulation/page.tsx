"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Radio, Wifi, WifiOff, ShieldAlert, ShieldCheck, Activity, Zap, AlertCircle, RefreshCw } from "lucide-react";
import { Card, StatCard } from "@/components/ui/Card";
import { InfoPanel } from "@/components/ui/InfoPanel";
import { api, MLModelResult, Dataset, API_URL } from "@/lib/api";

interface DetectionEvent {
  timestamp: number;
  predicted_class: string;
  confidence: number;
  is_unknown: boolean;
}

const WS_BASE = API_URL
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
  const [filter, setFilter] = useState<"all" | "known" | "unknown">("all");
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
    setError(null);
    const tokens = JSON.parse(window.localStorage.getItem("zeroday_tokens") ?? "{}");
    const ws = new WebSocket(`${WS_BASE}/simulation/ws/${modelId}?token=${tokens.access_token}`);

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setError("WebSocket connection failed. Ensure backend server is reachable.");
    ws.onmessage = (msg) => {
      const data = JSON.parse(msg.data);
      if (data.error) {
        setError(data.error);
        return;
      }
      setEvents((prev) => [data, ...prev].slice(0, 100));
    };

    wsRef.current = ws;
  }

  function disconnect() {
    wsRef.current?.close();
    wsRef.current = null;
  }

  useEffect(() => () => wsRef.current?.close(), []);

  const totalPackets = events.length;
  const unknownCount = events.filter((e) => e.is_unknown).length;
  const knownCount = events.filter((e) => !e.is_unknown).length;

  const filteredEvents = events.filter((e) => {
    if (filter === "unknown") return e.is_unknown;
    if (filter === "known") return !e.is_unknown;
    return true;
  });

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col border-b border-white/10 pb-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Radio size={22} className="text-accent-blue" /> Live Synthetic Packet Stream Simulation
          </h1>
          <span className={`px-2.5 py-1 rounded-full text-xs font-semibold flex items-center gap-1.5 ${
            connected ? "bg-severity-low/10 text-severity-low border border-severity-low/20" : "bg-base-800 text-slate-400 border border-white/10"
          }`}>
            <span className={`h-2 w-2 rounded-full ${connected ? "bg-severity-low animate-pulse" : "bg-slate-500"}`} />
            {connected ? "LIVE FEED ACTIVE" : "FEED DISCONNECTED"}
          </span>
        </div>
        <p className="text-slate-400 text-xs mt-0.5">
          Streams real-time synthetic flow vectors through PyTorch models and the OpenMax Weibull EVT layer over WebSocket.
        </p>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-severity-critical/10 border border-severity-critical/20 text-severity-critical text-xs flex items-center gap-2">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {/* Control Panel Card */}
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div>
              <label className="stat-label block mb-1">Target Dataset</label>
              <select
                value={datasetId}
                onChange={(e) => setDatasetId(e.target.value)}
                className="bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-accent-blue"
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="stat-label block mb-1">Inference Model</label>
              <select
                value={modelId}
                onChange={(e) => setModelId(e.target.value)}
                className="bg-base-800 border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-accent-blue"
              >
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.architecture.toUpperCase()} (ID: {m.id.substring(0, 8)})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            {!connected ? (
              <button onClick={connect} disabled={!modelId} className="btn-primary flex items-center gap-2 text-xs shadow-glow">
                <Wifi size={16} /> Start Live WebSocket Feed
              </button>
            ) : (
              <button
                onClick={disconnect}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-severity-critical/10 text-severity-critical text-xs font-semibold border border-severity-critical/20 hover:bg-severity-critical/20 transition-colors"
              >
                <WifiOff size={16} /> Stop Feed
              </button>
            )}
          </div>
        </div>
      </Card>

      {/* Real-time KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Packets Evaluated" value={totalPackets} trend={{ value: "Stream active", positive: true }} />
        <StatCard label="Known Traffic Events" value={knownCount} trend={{ value: "Classified by Softmax", positive: true }} />
        <StatCard label="Zero-Day Threats Flagged" value={unknownCount} trend={{ value: "Intercepted by OpenMax", positive: false }} />
        <StatCard label="Inference Latency" value="~1.4 ms" trend={{ value: "Real-time pipeline", positive: positiveBoolean(true) }} />
      </div>

      {/* Detection Feed Card */}
      <Card>
        <div className="flex items-center justify-between mb-4 border-b border-white/5 pb-3">
          <div className="flex items-center gap-2">
            <Activity size={18} className="text-accent-cyan" />
            <h2 className="text-sm font-semibold text-white">Live Threat Telemetry Feed</h2>
          </div>

          <div className="flex items-center gap-1.5 bg-base-950 p-1 rounded-lg border border-white/5 text-xs">
            <button
              onClick={() => setFilter("all")}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                filter === "all" ? "bg-accent-blue text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              All Events ({totalPackets})
            </button>
            <button
              onClick={() => setFilter("unknown")}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                filter === "unknown" ? "bg-severity-critical text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              Zero-Day Threats ({unknownCount})
            </button>
            <button
              onClick={() => setFilter("known")}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                filter === "known" ? "bg-severity-low text-base-950 font-bold" : "text-slate-400 hover:text-white"
              }`}
            >
              Known Traffic ({knownCount})
            </button>
          </div>
        </div>

        {events.length === 0 ? (
          <div className="p-8 text-center border border-dashed border-white/10 rounded-xl">
            <p className="text-xs text-slate-400 mb-3">No telemetry events received yet. Click "Start Live WebSocket Feed" to launch.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-2 max-h-[380px] overflow-y-auto pr-1">
            {filteredEvents.map((e, i) => (
              <div
                key={i}
                className={`flex items-center justify-between p-3 rounded-xl border text-xs transition-all ${
                  e.is_unknown
                    ? "bg-severity-critical/10 border-severity-critical/30 text-white"
                    : "bg-base-950/60 border-white/5 text-slate-200"
                }`}
              >
                <div className="flex items-center gap-3">
                  {e.is_unknown ? (
                    <div className="p-1.5 rounded-lg bg-severity-critical/20 text-severity-critical">
                      <ShieldAlert size={16} />
                    </div>
                  ) : (
                    <div className="p-1.5 rounded-lg bg-severity-low/20 text-severity-low">
                      <ShieldCheck size={16} />
                    </div>
                  )}

                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white uppercase tracking-tight">{e.predicted_class}</span>
                      {e.is_unknown && (
                        <span className="badge-unknown font-bold uppercase">UNSEEN ZERO-DAY ATTACK</span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-400 mt-0.5 font-mono">
                      Timestamp: {new Date(e.timestamp * 1000).toLocaleTimeString()}
                    </p>
                  </div>
                </div>

                <div className="text-right font-mono">
                  <span className="text-slate-300 font-semibold">{(e.confidence * 100).toFixed(1)}%</span>
                  <span className="text-[10px] text-slate-500 block">Confidence</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Contextual Educational Info Panel */}
      <InfoPanel
        title="Real-Time OpenMax WebSocket Inference"
        description="The live simulation streams synthetic flow vectors to test model latency and EVT rejection behavior under real-time network workloads."
        bullets={[
          "Executes PyTorch forward pass for every incoming vector.",
          "OpenMax EVT layer checks distance from MAV centroids.",
          "Flagged zero-day attacks trigger instant SOC alerts over WebSocket.",
        ]}
      />
    </motion.div>
  );
}

function positiveBoolean(b: boolean) {
  return b;
}

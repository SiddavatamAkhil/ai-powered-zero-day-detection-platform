"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Settings, ShieldCheck, User, Bell, Key, RefreshCw, AlertCircle } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [profile, setProfile] = useState<{ email: string; full_name: string; role: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .me()
      .then(setProfile)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-6 max-w-2xl">
      {/* Header */}
      <div className="flex flex-col border-b border-white/10 pb-4">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Settings size={22} className="text-accent-blue" /> Account & System Configuration
        </h1>
        <p className="text-slate-400 text-xs mt-0.5">Manage user credentials, SOC notification preferences, and platform API keys.</p>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-severity-critical/10 border border-severity-critical/20 text-severity-critical text-xs flex items-center gap-2">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {/* Profile Info Card */}
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <User size={18} className="text-accent-cyan" />
          <h2 className="text-sm font-semibold text-white">Current User Profile</h2>
        </div>

        {loading ? (
          <p className="text-xs text-slate-400 py-4 flex items-center gap-2">
            <RefreshCw size={14} className="animate-spin text-accent-blue" /> Fetching profile metadata...
          </p>
        ) : profile ? (
          <div className="flex flex-col gap-3 text-xs">
            <div className="flex justify-between border-b border-white/5 pb-2.5">
              <span className="text-slate-400">Full Name</span>
              <span className="text-white font-medium">{profile.full_name}</span>
            </div>
            <div className="flex justify-between border-b border-white/5 pb-2.5">
              <span className="text-slate-400">Email Address</span>
              <span className="text-white font-mono">{profile.email}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Assigned System Role</span>
              <span className="badge-known font-semibold uppercase">{profile.role}</span>
            </div>
          </div>
        ) : (
          <p className="text-xs text-slate-400">Profile metadata unavailable.</p>
        )}
      </Card>

      {/* Notification Preferences */}
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <Bell size={18} className="text-accent-blue" />
          <h2 className="text-sm font-semibold text-white">SOC Notification Preferences</h2>
        </div>

        <div className="flex flex-col gap-3 text-xs">
          {[
            { label: "PyTorch Model Training Run Completed", desc: "Notify when model training and OpenMax calibration finishes" },
            { label: "Dataset Processing & Parquet Engineering", desc: "Notify when standard feature scaling completes" },
            { label: "Unseen Zero-Day Threat Interception Alert", desc: "Trigger high-priority WebSocket alerts on unknown attack rejection" },
          ].map((item) => (
            <label key={item.label} className="flex items-start justify-between p-2.5 rounded-xl bg-base-950/60 border border-white/5 cursor-pointer">
              <div>
                <span className="text-slate-200 font-medium block">{item.label}</span>
                <span className="text-[11px] text-slate-400">{item.desc}</span>
              </div>
              <input type="checkbox" defaultChecked className="mt-1 h-4 w-4 rounded accent-accent-blue cursor-pointer" />
            </label>
          ))}
        </div>
      </Card>
    </motion.div>
  );
}

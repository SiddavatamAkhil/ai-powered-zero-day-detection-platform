"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [profile, setProfile] = useState<{ email: string; full_name: string; role: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.me().then(setProfile).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="flex flex-col gap-6 max-w-xl">
      <div>
        <h1 className="text-xl font-semibold text-white">Settings</h1>
        <p className="text-slate-400 text-sm">Account information and preferences.</p>
      </div>

      {error && <p className="text-severity-critical text-sm">{error}</p>}

      <Card>
        <h2 className="text-white font-medium mb-4">Profile</h2>
        {profile ? (
          <div className="flex flex-col gap-3 text-sm">
            <div className="flex justify-between border-b border-white/5 pb-2">
              <span className="text-slate-400">Name</span>
              <span className="text-white">{profile.full_name}</span>
            </div>
            <div className="flex justify-between border-b border-white/5 pb-2">
              <span className="text-slate-400">Email</span>
              <span className="text-white">{profile.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Role</span>
              <span className="badge-known">{profile.role}</span>
            </div>
          </div>
        ) : (
          <p className="text-slate-400 text-sm">Loading...</p>
        )}
      </Card>

      <Card>
        <h2 className="text-white font-medium mb-4">Notification Preferences</h2>
        <div className="flex flex-col gap-3 text-sm">
          {["Training run completed", "Dataset processing finished", "New unknown-attack detection"].map((label) => (
            <label key={label} className="flex items-center justify-between">
              <span className="text-slate-300">{label}</span>
              <input type="checkbox" defaultChecked className="accent-accent-blue" />
            </label>
          ))}
        </div>
      </Card>
    </div>
  );
}

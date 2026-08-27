"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Users, RefreshCw, AlertCircle, ShieldCheck, UserCheck } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { apiFetch } from "@/lib/api";

interface UserRow {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "analyst" | "viewer";
  is_active: boolean;
}

export default function UsersPage() {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  function refresh() {
    setLoading(true);
    apiFetch<UserRow[]>("/users")
      .then(setUsers)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function updateRole(userId: string, role: string) {
    try {
      await apiFetch(`/users/${userId}/role`, { method: "PATCH", body: JSON.stringify({ role }) });
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update user role.");
    }
  }

  async function toggleActive(userId: string, isActive: boolean) {
    try {
      await apiFetch(`/users/${userId}/active`, { method: "PATCH", body: JSON.stringify({ is_active: !isActive }) });
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update user status.");
    }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-6 max-w-4xl">
      {/* Header */}
      <div className="flex flex-col border-b border-white/10 pb-4">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Users size={22} className="text-accent-blue" /> Access Control & User Management
        </h1>
        <p className="text-slate-400 text-xs mt-0.5">
          Admin privilege control. Manage user accounts, role allocations (Admin, Analyst, Viewer), and active access status.
        </p>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-severity-critical/10 border border-severity-critical/20 text-severity-critical text-xs flex items-center gap-2">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {/* Users Table */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white">Registered User Accounts</h2>
          <span className="text-xs text-slate-400">{users.length} accounts</span>
        </div>

        {loading ? (
          <p className="text-xs text-slate-400 py-8 text-center flex items-center justify-center gap-2">
            <RefreshCw size={14} className="animate-spin text-accent-blue" /> Loading user registry...
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-slate-400 border-b border-white/5">
                  <th className="pb-2.5 font-semibold">User Name</th>
                  <th className="pb-2.5 font-semibold">Email Address</th>
                  <th className="pb-2.5 font-semibold">Assigned Role</th>
                  <th className="pb-2.5 font-semibold text-right">Account Status</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-white/5 last:border-0 hover:bg-white/[0.02]">
                    <td className="py-3 text-white font-medium flex items-center gap-2">
                      <div className="flex h-6 w-6 items-center justify-center rounded bg-accent-blue/20 text-accent-blue font-bold text-[10px]">
                        {u.full_name.charAt(0).toUpperCase()}
                      </div>
                      {u.full_name}
                    </td>
                    <td className="py-3 text-slate-300 font-mono">{u.email}</td>
                    <td className="py-3">
                      <select
                        value={u.role}
                        onChange={(e) => updateRole(u.id, e.target.value)}
                        className="bg-base-800 border border-white/10 rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none focus:border-accent-blue font-medium"
                      >
                        <option value="viewer">Viewer</option>
                        <option value="analyst">Analyst</option>
                        <option value="admin">Admin</option>
                      </select>
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => toggleActive(u.id, u.is_active)}
                        className={u.is_active ? "badge-known cursor-pointer" : "badge-unknown cursor-pointer"}
                      >
                        {u.is_active ? "Active" : "Deactivated"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </motion.div>
  );
}

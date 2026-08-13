"use client";

import { useEffect, useState } from "react";
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

  function refresh() {
    apiFetch<UserRow[]>("/users").then(setUsers).catch((e) => setError(e.message));
  }
  useEffect(refresh, []);

  async function updateRole(userId: string, role: string) {
    try {
      await apiFetch(`/users/${userId}/role`, { method: "PATCH", body: JSON.stringify({ role }) });
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update role.");
    }
  }

  async function toggleActive(userId: string, isActive: boolean) {
    try {
      await apiFetch(`/users/${userId}/active`, { method: "PATCH", body: JSON.stringify({ is_active: !isActive }) });
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update status.");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-white">User Management</h1>
        <p className="text-slate-400 text-sm">Admin-only. Requires the admin role on your account.</p>
      </div>

      {error && <p className="text-severity-critical text-sm">{error}</p>}

      <Card>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-400 border-b border-white/5">
              <th className="pb-2 font-normal">Name</th>
              <th className="pb-2 font-normal">Email</th>
              <th className="pb-2 font-normal">Role</th>
              <th className="pb-2 font-normal">Status</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-white/5 last:border-0">
                <td className="py-2 text-white">{u.full_name}</td>
                <td className="py-2 text-slate-300">{u.email}</td>
                <td className="py-2">
                  <select
                    value={u.role}
                    onChange={(e) => updateRole(u.id, e.target.value)}
                    className="bg-base-800 border border-white/10 rounded-lg px-2 py-1 text-xs text-white"
                  >
                    <option value="viewer">Viewer</option>
                    <option value="analyst">Analyst</option>
                    <option value="admin">Admin</option>
                  </select>
                </td>
                <td className="py-2">
                  <button
                    onClick={() => toggleActive(u.id, u.is_active)}
                    className={u.is_active ? "badge-known" : "badge-unknown"}
                  >
                    {u.is_active ? "Active" : "Deactivated"}
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

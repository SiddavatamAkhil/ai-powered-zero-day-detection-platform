"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import clsx from "clsx";
import {
  LayoutDashboard,
  Database,
  Cpu,
  GitCompare,
  FileText,
  Settings,
  Users,
  ScrollText,
  ShieldAlert,
  Brain,
  Radio,
  Sparkles,
  LogOut,
  UserCheck,
} from "lucide-react";
import { api, clearTokens } from "@/lib/api";
import { useDemo } from "./DemoContext";

interface NavSection {
  title: string;
  items: {
    href: string;
    label: string;
    icon: any;
    badge?: string;
  }[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: "OVERVIEW",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    ],
  },
  {
    title: "DATA PIPELINE",
    items: [
      { href: "/datasets", label: "Datasets & Splits", icon: Database },
    ],
  },
  {
    title: "AI SECURITY ENGINE",
    items: [
      { href: "/training", label: "Model Training", icon: Cpu },
      { href: "/models", label: "Model Comparison", icon: GitCompare },
      { href: "/explainability", label: "SHAP Explainability", icon: Brain },
    ],
  },
  {
    title: "INSIGHTS & ACTION",
    items: [
      { href: "/simulation", label: "Live Simulation", icon: Radio, badge: "WS" },
      { href: "/reports", label: "PDF Reports", icon: FileText },
    ],
  },
  {
    title: "ADMIN / SYSTEM",
    items: [
      { href: "/users", label: "User Management", icon: Users },
      { href: "/logs", label: "Audit Logs", icon: ScrollText },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { active: isDemoActive, startDemo } = useDemo();
  const [profile, setProfile] = useState<{ email: string; full_name: string; role: string } | null>(null);

  useEffect(() => {
    api.me().then(setProfile).catch(() => setProfile(null));
  }, [pathname]);

  function handleLogout() {
    clearTokens();
    router.push("/login");
  }

  return (
    <aside className="w-64 shrink-0 h-screen sticky top-0 border-r border-white/10 bg-base-900/90 backdrop-blur-md p-4 flex flex-col justify-between select-none">
      <div className="flex flex-col gap-5 overflow-y-auto pr-1">
        {/* Platform Branding */}
        <div className="flex items-center gap-2.5 px-2 py-1.5 border-b border-white/5 pb-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-blue/10 text-accent-blue border border-accent-blue/20 shadow-glow">
            <ShieldAlert size={20} />
          </div>
          <div>
            <span className="font-bold text-white text-sm tracking-tight leading-none block">
              ZeroDay Platform
            </span>
            <span className="text-slate-400 font-normal text-[11px] block mt-0.5">
              AI Cyber Threat Engine
            </span>
          </div>
        </div>

        {/* Guided Demo Button */}
        <button
          onClick={startDemo}
          className={clsx(
            "w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl font-semibold text-xs transition-all shadow-glow",
            isDemoActive
              ? "bg-accent-cyan text-base-950 ring-2 ring-accent-cyan/50 animate-pulse"
              : "bg-gradient-to-r from-accent-blue to-accent-purple text-white hover:opacity-95"
          )}
        >
          <Sparkles size={16} />
          <span>{isDemoActive ? "Guided Demo Active" : "Start Guided Demo"}</span>
        </button>

        {/* Navigation Sections */}
        <nav className="flex flex-col gap-4">
          {NAV_SECTIONS.map((section) => (
            <div key={section.title} className="flex flex-col gap-1">
              <span className="px-2 text-[10px] font-bold tracking-wider text-slate-500 uppercase">
                {section.title}
              </span>
              {section.items.map(({ href, label, icon: Icon, badge }) => {
                const active = pathname?.startsWith(href);
                return (
                  <Link
                    key={href}
                    href={href}
                    className={clsx("nav-link flex items-center justify-between", active && "nav-link-active")}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon size={16} className={active ? "text-accent-blue" : "text-slate-400"} />
                      <span className="text-xs">{label}</span>
                    </div>
                    {badge && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-accent-blue/20 text-accent-blue border border-accent-blue/30">
                        {badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
      </div>

      {/* User Footer Card */}
      <div className="pt-3 border-t border-white/10 mt-2">
        {profile ? (
          <div className="flex items-center justify-between p-2 rounded-xl bg-base-800/80 border border-white/5">
            <div className="flex items-center gap-2 truncate">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent-blue/20 text-accent-blue font-bold text-xs shrink-0">
                {profile.full_name?.charAt(0).toUpperCase() || "U"}
              </div>
              <div className="truncate">
                <p className="text-xs font-medium text-white truncate leading-tight">{profile.full_name}</p>
                <span className="text-[10px] text-accent-cyan uppercase font-semibold">{profile.role}</span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="text-slate-400 hover:text-severity-critical p-1.5 rounded-lg hover:bg-white/5 transition-colors"
              title="Logout"
            >
              <LogOut size={16} />
            </button>
          </div>
        ) : (
          <Link
            href="/login"
            className="flex items-center justify-center gap-2 text-xs text-slate-400 hover:text-white py-2"
          >
            <UserCheck size={14} /> Log In
          </Link>
        )}
      </div>
    </aside>
  );
}

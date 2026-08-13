"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
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
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/datasets", label: "Datasets", icon: Database },
  { href: "/training", label: "Training", icon: Cpu },
  { href: "/models", label: "Model Comparison", icon: GitCompare },
  { href: "/explainability", label: "Explainability", icon: Brain },
  { href: "/simulation", label: "Live Simulation", icon: Radio },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/logs", label: "Logs", icon: ScrollText },
  { href: "/users", label: "User Management", icon: Users },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 shrink-0 h-screen sticky top-0 border-r border-white/5 bg-base-900/80 backdrop-blur-xs p-4 flex flex-col gap-6">
      <div className="flex items-center gap-2 px-2 py-1">
        <ShieldAlert className="text-accent-blue" size={22} />
        <span className="font-semibold text-white text-sm leading-tight">
          Zero-Day Detection<br />
          <span className="text-slate-400 font-normal text-xs">Platform</span>
        </span>
      </div>

      <nav className="flex flex-col gap-1">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname?.startsWith(href);
          return (
            <Link key={href} href={href} className={clsx("nav-link", active && "nav-link-active")}>
              <Icon size={16} />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

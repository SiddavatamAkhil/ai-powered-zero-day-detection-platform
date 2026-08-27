import React, { useState } from "react";
import { Info, ChevronDown, ChevronUp, Sparkles } from "lucide-react";
import clsx from "clsx";

interface InfoPanelProps {
  title: string;
  description: string;
  bullets?: string[];
  badge?: string;
  defaultExpanded?: boolean;
  className?: string;
}

export function InfoPanel({
  title,
  description,
  bullets,
  badge = "Cybersecurity Intelligence",
  defaultExpanded = true,
  className,
}: InfoPanelProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div
      className={clsx(
        "rounded-xl border border-accent-blue/20 bg-gradient-to-r from-base-900/90 to-base-800/80 p-4 shadow-glass backdrop-blur-xs transition-all",
        className
      )}
    >
      <div className="flex items-center justify-between cursor-pointer select-none" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-blue/10 text-accent-blue border border-accent-blue/20">
            <Sparkles size={16} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-white">{title}</h3>
              {badge && (
                <span className="rounded-full bg-accent-blue/10 px-2 py-0.5 text-[10px] font-medium text-accent-blue border border-accent-blue/20">
                  {badge}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">{description}</p>
          </div>
        </div>
        <button className="text-slate-400 hover:text-white p-1">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {expanded && bullets && bullets.length > 0 && (
        <div className="mt-3 border-t border-white/5 pt-3 pl-11">
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-slate-300">
            {bullets.map((b, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-accent-cyan shrink-0" />
                <span>{b}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

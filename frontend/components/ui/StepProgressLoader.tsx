import React from "react";
import { CheckCircle2, Circle, Loader2, AlertCircle } from "lucide-react";
import clsx from "clsx";

export interface ProgressStage {
  id: string;
  label: string;
  status: "completed" | "active" | "pending" | "failed";
  detail?: string;
}

interface StepProgressLoaderProps {
  title: string;
  stages: ProgressStage[];
  onRetry?: () => void;
  className?: string;
}

export function StepProgressLoader({ title, stages, onRetry, className }: StepProgressLoaderProps) {
  return (
    <div className={clsx("rounded-xl border border-white/10 bg-base-900/90 p-5 shadow-glass backdrop-blur-xs", className)}>
      <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
        <Loader2 size={16} className="animate-spin text-accent-blue" />
        {title}
      </h3>

      <div className="flex flex-col gap-3">
        {stages.map((stage) => (
          <div key={stage.id} className="flex items-start gap-3 text-xs">
            <div className="mt-0.5 shrink-0">
              {stage.status === "completed" && <CheckCircle2 size={16} className="text-severity-low" />}
              {stage.status === "active" && <Loader2 size={16} className="animate-spin text-accent-blue" />}
              {stage.status === "pending" && <Circle size={16} className="text-slate-600" />}
              {stage.status === "failed" && <AlertCircle size={16} className="text-severity-critical" />}
            </div>

            <div className="flex-1">
              <span
                className={clsx(
                  "font-medium",
                  stage.status === "completed" && "text-slate-200 line-through opacity-80",
                  stage.status === "active" && "text-white font-semibold",
                  stage.status === "pending" && "text-slate-500",
                  stage.status === "failed" && "text-severity-critical font-semibold"
                )}
              >
                {stage.label}
              </span>
              {stage.detail && <p className="text-[11px] text-slate-400 mt-0.5">{stage.detail}</p>}
            </div>
          </div>
        ))}
      </div>

      {stages.some((s) => s.status === "failed") && onRetry && (
        <div className="mt-4 pt-3 border-t border-white/5 flex justify-end">
          <button
            onClick={onRetry}
            className="px-3 py-1.5 rounded-lg bg-severity-critical/10 text-severity-critical text-xs font-medium border border-severity-critical/20 hover:bg-severity-critical/20 transition-colors"
          >
            Retry Step
          </button>
        </div>
      )}
    </div>
  );
}

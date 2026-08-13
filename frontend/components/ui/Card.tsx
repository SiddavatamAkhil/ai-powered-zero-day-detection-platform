import { ReactNode } from "react";
import clsx from "clsx";

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx("glass-card", className)}>{children}</div>;
}

export function StatCard({
  label,
  value,
  trend,
}: {
  label: string;
  value: string | number;
  trend?: { value: string; positive: boolean };
}) {
  return (
    <Card className="flex flex-col gap-1">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {trend && (
        <span className={clsx("text-xs", trend.positive ? "text-severity-low" : "text-severity-critical")}>
          {trend.value}
        </span>
      )}
    </Card>
  );
}

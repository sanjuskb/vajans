import React from "react";
import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { clsx } from "clsx";

interface Props {
  label: string;
  value: string | number;
  sub?: string;
  trend?: number;
  accent?: boolean;
  alert?: boolean;
  icon?: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export default function MetricCard({
  label, value, sub, trend, accent, alert, icon, className, onClick,
}: Props) {
  const TrendIcon = trend === undefined || trend === 0
    ? Minus
    : trend > 0 ? TrendingUp : TrendingDown;

  const trendColor = trend === undefined
    ? "text-text-tertiary"
    : trend > 0 ? "text-success" : "text-danger";

  return (
    <motion.div
      whileHover={{ y: -2, boxShadow: "0 4px 16px rgba(0,0,0,0.25)" }}
      transition={{ type: "spring", stiffness: 400, damping: 28 }}
      className={clsx(
        "bg-bg-secondary border border-border-subtle rounded-lg p-8",
        accent && "bg-accent-muted border-accent-primary/25",
        alert && "bg-fail-bg border-fail/25",
        onClick && "cursor-pointer",
        className
      )}
      onClick={onClick}
    >
      <div className="flex justify-between items-start mb-4">
        <span className="text-sm text-text-secondary font-medium">{label}</span>
        {icon && <span className="opacity-50">{icon}</span>}
      </div>
      <div className={clsx(
        "text-4xl font-bold leading-tight tabular-nums",
        accent ? "text-accent-text" : alert ? "text-fail-text" : "text-text-primary"
      )}>
        {value}
      </div>
      {(sub || trend !== undefined) && (
        <div className="flex items-center gap-1 mt-3">
          {trend !== undefined && (
            <span className={`flex items-center gap-1 text-xs ${trendColor}`}>
              <TrendIcon size={12} />
              {Math.abs(trend)}%
            </span>
          )}
          {sub && <span className="text-xs text-text-tertiary">{sub}</span>}
        </div>
      )}
    </motion.div>
  );
}

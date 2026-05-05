import { clsx } from "clsx";

interface Props {
  value: number;  // 0-1
  size?: "sm" | "md";
  showLabel?: boolean;
  className?: string;
}

export default function TrustBar({ value, size = "sm", showLabel = false, className }: Props) {
  const pct = Math.round(value * 100);
  const color = value >= 0.85
    ? "bg-pass"
    : value >= 0.6
    ? "bg-uncertain"
    : "bg-fail";

  const height = size === "sm" ? "h-1" : "h-1.5";

  return (
    <div className={clsx("flex items-center gap-2", className)}>
      <div className={clsx("flex-1 bg-bg-tertiary rounded-full overflow-hidden", height)}>
        <div
          className={clsx("h-full rounded-full transition-all duration-300", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <span className={clsx(
          "text-xs font-mono font-semibold min-w-7 text-right",
          value >= 0.85 ? "text-pass" : value >= 0.6 ? "text-uncertain" : "text-fail"
        )}>
          {pct}%
        </span>
      )}
    </div>
  );
}

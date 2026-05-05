import { clsx } from "clsx";

export type BadgeVariant =
  | "pass" | "fail" | "uncertain" | "review"
  | "mandatory" | "preferred" | "processing" | "completed" | "failed"
  | "draft" | "pending" | "info" | "neutral" | "high" | "normal" | "low";

const variants: Record<BadgeVariant, string> = {
  pass: "bg-pass-bg text-pass-text",
  fail: "bg-fail-bg text-fail-text",
  uncertain: "bg-uncertain-bg text-uncertain-text",
  review: "bg-review-bg text-review-text",
  mandatory: "bg-accent-muted text-accent-text",
  preferred: "bg-bg-tertiary text-text-secondary",
  processing: "bg-blue-950 text-blue-400",
  completed: "bg-pass-bg text-pass-text",
  failed: "bg-fail-bg text-fail-text",
  draft: "bg-bg-tertiary text-text-tertiary",
  pending: "bg-uncertain-bg text-uncertain-text",
  info: "bg-cyan-950 text-cyan-400",
  neutral: "bg-bg-tertiary text-text-secondary",
  high: "bg-fail-bg text-fail-text",
  normal: "bg-accent-muted text-accent-text",
  low: "bg-bg-tertiary text-text-secondary",
};

interface Props {
  variant: BadgeVariant;
  label?: string;
  dot?: boolean;
  className?: string;
}

export default function Badge({ variant, label, dot, className }: Props) {
  const text = label ?? variant.toUpperCase().replace(/_/g, " ");
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 h-5.5 px-2 rounded text-xs font-semibold tracking-wider uppercase whitespace-nowrap flex-shrink-0",
        variants[variant] ?? variants.neutral,
        className
      )}
    >
      {dot && (
        <span className="w-1.5 h-1.5 rounded-full bg-current flex-shrink-0" />
      )}
      {text}
    </span>
  );
}

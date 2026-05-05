import React from "react";
import { clsx } from "clsx";

interface CardProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
  padding?: "sm" | "md" | "lg" | "xl";
  hoverable?: boolean;
  className?: string;
}

const paddings = {
  sm: "p-3",
  md: "p-4",
  lg: "p-6",
  xl: "p-8",
};

export default function Card({
  children,
  title,
  subtitle,
  actions,
  padding = "xl",
  hoverable,
  className,
}: CardProps) {
  return (
    <div
      className={clsx(
        "bg-bg-secondary border border-border-subtle rounded-lg transition-colors",
        hoverable && "hover:border-border-active",
        paddings[padding],
        className
      )}
    >
      {(title || actions) && (
        <div className="flex justify-between items-center mb-6 pb-3 border-b border-border-subtle">
          {title && (
            <div>
              <h3 className="text-base font-semibold text-text-primary">{title}</h3>
              {subtitle && <p className="text-sm text-text-secondary mt-0.5">{subtitle}</p>}
            </div>
          )}
          {actions && <div className="flex gap-2 items-center">{actions}</div>}
        </div>
      )}
      {children}
    </div>
  );
}

// Skeleton card
export function CardSkeleton({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={clsx("bg-bg-secondary border border-border-subtle rounded-lg p-8", className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="skeleton rounded mb-2.5 last:mb-0"
          style={{
            height: 14,
            width: i === 0 ? "60%" : i === lines - 1 ? "40%" : "100%"
          }}
        />
      ))}
    </div>
  );
}

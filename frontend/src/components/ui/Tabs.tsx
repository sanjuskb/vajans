import React from "react";
import { clsx } from "clsx";

interface Tab {
  id: string;
  label: string;
  icon?: React.ReactNode;
  badge?: number;
}

interface Props {
  tabs: Tab[];
  active: string;
  onChange: (id: string) => void;
  className?: string;
}

export default function Tabs({ tabs, active, onChange, className }: Props) {
  return (
    <div className={clsx("flex gap-0.5 border-b border-border-subtle mb-8", className)}>
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={clsx(
              "flex items-center gap-1 px-4 py-3",
              "bg-transparent border-0 cursor-pointer",
              "text-sm font-medium whitespace-nowrap",
              "transition-colors -mb-px",
              isActive
                ? "text-accent-text border-b-2 border-accent-primary"
                : "text-text-secondary border-b-2 border-transparent hover:text-text-primary"
            )}
          >
            {tab.icon}
            {tab.label}
            {tab.badge !== undefined && tab.badge > 0 && (
              <span className="bg-accent-primary text-white rounded-full text-xs font-bold px-1.5 py-0.5 leading-tight">
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

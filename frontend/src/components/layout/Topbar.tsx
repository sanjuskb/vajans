import React from "react";
import { Bell, Search, Plus } from "lucide-react";
import Button from "../ui/Button";

interface TopbarProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export default function Topbar({ title, subtitle, actions }: TopbarProps) {
  return (
    <header className="h-14 bg-bg-primary border-b border-border-subtle flex items-center justify-between px-6">
      {/* Left: Title & Breadcrumb */}
      <div>
        <h1 className="text-h4 font-semibold text-text-primary">{title}</h1>
        {subtitle && (
          <p className="text-caption text-text-secondary mt-0.5">{subtitle}</p>
        )}
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-4">
        {/* Search */}
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-text-tertiary" />
          <input
            type="text"
            placeholder="Search..."
            className="w-64 pl-9 pr-4 py-2 bg-bg-tertiary border border-border-subtle rounded-md text-sm text-text-primary placeholder-text-tertiary focus:border-accent-primary focus:outline-none"
          />
        </div>

        {/* Notifications */}
        <Button variant="icon" className="relative">
          <Bell size={18} />
          <span className="absolute -top-1 -right-1 w-2 h-2 bg-fail rounded-full"></span>
        </Button>

        {/* New Evaluation CTA */}
        <Button variant="primary" size="md" icon={<Plus size={16} />}>
          New Evaluation
        </Button>

        {/* Custom Actions */}
        {actions}
      </div>
    </header>
  );
}
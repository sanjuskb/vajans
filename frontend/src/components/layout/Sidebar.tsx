import React, { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  FolderOpen,
  ShieldCheck,
  FileText,
  Settings,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
  Bell,
  Search,
  Plus
} from "lucide-react";
import Logo from "../ui/Logo";
import Button from "../ui/Button";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/jobs", label: "Jobs", icon: FolderOpen },
  { to: "/review", label: "Review Queue", icon: ShieldCheck, badge: 3 },
  { to: "/audit", label: "Audit Logs", icon: FileText },
];

const systemItems = [
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/help", label: "Help", icon: HelpCircle },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <aside className={`bg-bg-primary border-r border-border-subtle flex flex-col flex-shrink-0 transition-all duration-300 ${
      collapsed ? 'w-16' : 'w-60'
    }`}>
      {/* Header */}
      <div className="h-14 border-b border-border-subtle flex items-center justify-between px-4">
        {!collapsed && <Logo size="sm" />}
        <Button
          variant="icon"
          onClick={onToggle}
          className="text-text-secondary hover:text-text-primary"
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4">
        <div className="space-y-1">
          {navItems.map(({ to, label, icon: Icon, badge }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-accent-primary text-white'
                    : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
                }`
              }
            >
              <Icon size={18} />
              {!collapsed && (
                <>
                  <span className="flex-1">{label}</span>
                  {badge && badge > 0 && (
                    <span className="bg-fail text-white text-xs font-bold px-1.5 py-0.5 rounded-full">
                      {badge}
                    </span>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </div>

        {/* System Section */}
        {!collapsed && (
          <div className="mt-8 pt-4 border-t border-border-subtle">
            <div className="px-3 mb-2">
              <span className="text-xs font-semibold text-text-tertiary uppercase tracking-wider">
                System
              </span>
            </div>
            <div className="space-y-1">
              {systemItems.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-accent-primary text-white'
                        : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
                    }`
                  }
                >
                  <Icon size={18} />
                  <span className="flex-1">{label}</span>
                </NavLink>
              ))}
            </div>
          </div>
        )}
      </nav>

      {/* User Section */}
      <div className="p-4 border-t border-border-subtle">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-accent-primary rounded-full flex items-center justify-center text-white text-sm font-semibold">
            JD
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-text-primary truncate">
                John Doe
              </div>
              <div className="text-xs text-text-tertiary">
                Procurement Officer
              </div>
            </div>
          )}
        </div>
        {!collapsed && (
          <button className="w-full mt-3 text-sm text-text-secondary hover:text-text-primary transition-colors">
            Sign Out
          </button>
        )}
      </div>
    </aside>
  );
}
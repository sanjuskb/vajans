import React, { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import Topbar from "./Topbar";

export default function Layout(): React.ReactElement {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const location = useLocation();

  // Get page title based on current route
  const getPageTitle = () => {
    const path = location.pathname;
    if (path === "/dashboard") return "Dashboard";
    if (path === "/jobs") return "Evaluations";
    if (path === "/review") return "Review Queue";
    if (path === "/audit") return "Audit Logs";
    if (path.startsWith("/jobs/")) return "Job Details";
    return "VAJANS";
  };

  return (
    <div className="min-h-screen bg-bg-primary flex">
      {/* Sidebar */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Topbar */}
        <Topbar title={getPageTitle()} />

        {/* Page Content */}
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

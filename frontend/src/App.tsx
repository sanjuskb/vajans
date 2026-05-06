import React, { useEffect } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";

import { useStore } from "./store/useStore";
import AppLayout    from "./layouts/AppLayout";
import MinimalLayout from "./layouts/MinimalLayout";

import LandingPage   from "./pages/LandingPage";
import LoginPage     from "./pages/LoginPage";
import AboutPage     from "./pages/AboutPage";
import DashboardPage from "./pages/DashboardPage";
import JobsPage      from "./pages/JobsPage";
import JobDetailPage from "./pages/JobDetailPage";
import AnalysisPage  from "./pages/AnalysisPage";
import ReviewPage    from "./pages/ReviewPage";
import AuditPage     from "./pages/AuditPage";
import SettingsPage  from "./pages/SettingsPage";
import NotFoundPage  from "./pages/NotFoundPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

function ThemeApplier() {
  const theme = useStore((s) => s.theme);
  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("dark", "light");
    root.classList.add(theme);
  }, [theme]);
  return null;
}

export default function App(): React.ReactElement {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeApplier />
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: "var(--tooltip-bg)",
              color: "var(--text-primary)",
              border: "1px solid var(--tooltip-border)",
              fontSize: 13,
            },
          }}
        />
        <Routes>
          {/* Public — minimal layout */}
          <Route element={<MinimalLayout />}>
            <Route path="/"      element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/about" element={<AboutPage />} />
          </Route>

          {/* Authenticated — app shell */}
          <Route element={<AppLayout />}>
            <Route path="/dashboard"    element={<DashboardPage />} />
            <Route path="/jobs"         element={<JobsPage />} />
            <Route path="/jobs/:jobId"  element={<JobDetailPage />} />
            <Route path="/analysis/:jobId/:bidderId" element={<AnalysisPage />} />
            <Route path="/review"       element={<ReviewPage />} />
            <Route path="/audit"        element={<AuditPage />} />
            <Route path="/settings"     element={<SettingsPage />} />
            <Route path="/help"         element={<HelpPlaceholder />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

function HelpPlaceholder() {
  return (
    <div style={{ color: "var(--text-secondary)", padding: 32, fontSize: 14 }}>
      Help &amp; Documentation — coming soon
    </div>
  );
}

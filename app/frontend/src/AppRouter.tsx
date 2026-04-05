import { Routes, Route } from "react-router-dom";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { GitHubCallbackPage } from "@/pages/GitHubCallbackPage";
import { OnboardingPage } from "@/pages/OnboardingPage";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppLayout } from "@/components/templates/AppLayout";
import { DashboardPage } from "@/pages/DashboardPage";
import { WorkspaceDetailPage } from "@/pages/WorkspaceDetailPage";
import { StackDetailPage } from "@/pages/StackDetailPage";

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/auth/github/callback" element={<GitHubCallbackPage />} />
      <Route
        path="/onboarding"
        element={
          <ProtectedRoute>
            <OnboardingPage />
          </ProtectedRoute>
        }
      />

      {/* Authenticated app with global sidebar */}
      <Route
        element={
          <ProtectedRoute>
            <AuthGate>
              <AppLayout />
            </AuthGate>
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="workspaces/:taskId" element={<WorkspaceDetailPage />} />
        <Route path="stacks/:stackId" element={<StackDetailPage />} />
        {/* Fallback: legacy route sends to dashboard */}
        <Route path="*" element={<DashboardPage />} />
      </Route>
    </Routes>
  );
}

/**
 * Auth gate that checks onboarding status and redirects if needed.
 * Extracted from the old App component.
 */
import { useEffect, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";
import { useAuth } from "@/hooks/useAuth";

interface OnboardingStatus {
  needs_onboarding: boolean;
  has_github: boolean;
  has_project: boolean;
}

function AuthGate({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const { data: onboardingStatus, isLoading } = useQuery<OnboardingStatus>({
    queryKey: ["onboarding", "status"],
    queryFn: () =>
      apiClient.get<OnboardingStatus>("/api/v1/onboarding/status"),
    enabled: isAuthenticated,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (onboardingStatus?.needs_onboarding) {
      navigate("/onboarding", { replace: true });
    }
  }, [onboardingStatus, navigate]);

  if (isLoading || !onboardingStatus) {
    return (
      <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] flex items-center justify-center">
        <p className="text-[var(--fg-muted)] text-sm">Loading...</p>
      </div>
    );
  }

  return <>{children}</>;
}

import { Routes, Route } from "react-router-dom";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { GitHubCallbackPage } from "@/pages/GitHubCallbackPage";
import { OnboardingPage } from "@/pages/OnboardingPage";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { App } from "./App";

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
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <App />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

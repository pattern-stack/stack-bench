import { Routes, Route } from "react-router-dom";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { App } from "./App";

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
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

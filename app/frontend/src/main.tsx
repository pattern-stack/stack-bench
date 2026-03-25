import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setApiConfig } from "@/generated/api/client";
import { AuthProvider } from "@/contexts/AuthContext";
import { AppRouter } from "./AppRouter";
import "./index.css";

// Configure generated API client — reads auth token from localStorage
setApiConfig({
  baseUrl: window.location.origin,
  getAuthToken: () => localStorage.getItem("access_token"),
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <QueryClientProvider client={queryClient}>
          <AppRouter />
        </QueryClientProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);

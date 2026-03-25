import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setApiConfig } from "@/generated/api/client";
import { AuthProvider } from "@/contexts/AuthContext";
import { getAccessToken } from "@/lib/auth";
import { AppRouter } from "./AppRouter";
import "./index.css";

// Configure generated API client with auth token getter
setApiConfig({
  baseUrl: window.location.origin,
  getAuthToken: getAccessToken,
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

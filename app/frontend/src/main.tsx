import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setApiConfig } from "@/generated/api/client";
import { App } from "./App";
import "./index.css";

// Configure generated API client — uses Vite proxy so no explicit baseUrl needed
setApiConfig({ baseUrl: window.location.origin });

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
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>
);

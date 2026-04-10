import { useState, useCallback } from "react";
import { Outlet } from "react-router-dom";
import { GlobalSidebar } from "@/components/organisms/GlobalSidebar";

const STORAGE_KEY = "stack-bench-sidebar-collapsed";

function AppLayout() {
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem(STORAGE_KEY) === "true"
  );

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEY, String(next));
      return next;
    });
  }, []);

  return (
    <div className="flex h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] font-[family-name:var(--font-sans)]">
      <GlobalSidebar collapsed={collapsed} onToggleCollapse={toggleCollapsed} />
      <main className="flex-1 flex flex-col min-w-0">
        <Outlet />
      </main>
    </div>
  );
}

AppLayout.displayName = "AppLayout";

export { AppLayout };

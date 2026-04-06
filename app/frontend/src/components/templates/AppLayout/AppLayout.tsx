import { Outlet } from "react-router-dom";
import { GlobalSidebar } from "@/components/organisms/GlobalSidebar";

function AppLayout() {
  return (
    <div className="flex h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] font-[family-name:var(--font-sans)]">
      <GlobalSidebar />
      <main className="flex-1 flex flex-col min-w-0">
        <Outlet />
      </main>
    </div>
  );
}

AppLayout.displayName = "AppLayout";

export { AppLayout };

"use client";

import React, { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";
import { DemoProvider } from "@/components/DemoContext";
import { GuidedDemoModal } from "@/components/GuidedDemoModal";

export function ClientLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isLoginPage = pathname === "/login";

  return (
    <DemoProvider>
      <div className="min-h-screen flex w-full bg-base-950 text-slate-100 font-sans antialiased">
        {!isLoginPage && <Sidebar />}
        <main className={`flex-1 ${isLoginPage ? "w-full p-0 flex items-center justify-center min-h-screen" : "p-6 md:p-8 max-w-[1400px] mx-auto w-full overflow-x-hidden"}`}>
          {children}
        </main>
        {!isLoginPage && <GuidedDemoModal />}
      </div>
    </DemoProvider>
  );
}

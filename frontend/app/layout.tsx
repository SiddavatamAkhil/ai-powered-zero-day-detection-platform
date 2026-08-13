import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "Zero-Day Attack Detection Platform",
  description: "Enterprise deep learning platform for zero-day attack classification.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen flex">
        <Sidebar />
        <main className="flex-1 p-8 max-w-[1400px] mx-auto w-full">{children}</main>
      </body>
    </html>
  );
}

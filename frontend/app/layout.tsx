import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";

export const metadata: Metadata = {
  title: "StrategyShifu — Knowledge Graph Intelligence",
  description:
    "LightRAG-powered knowledge graph application for strategy consulting intelligence",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-navy-950 text-slate-100 min-h-screen flex">
        {/* Sidebar */}
        <Sidebar />

        {/* Main content area */}
        <div className="flex-1 flex flex-col min-h-screen ml-64">
          <Header />
          <main className="flex-1 overflow-auto p-6 bg-navy-950">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}

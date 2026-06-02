import type { Metadata } from "next";
import { Nav } from "@/components/Nav";
import { MockDataBanner } from "@/components/MockDataBanner";
import "./globals.css";

export const metadata: Metadata = {
  title: "AIMS — AI 投资组合模拟决策系统",
  description: "研究—决策—模拟交易—复盘",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <Nav />
        <main className="mx-auto max-w-6xl p-4">
          <MockDataBanner />
          {children}
        </main>
      </body>
    </html>
  );
}

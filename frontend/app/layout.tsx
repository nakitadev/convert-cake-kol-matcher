import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Convert Cake — Thai TikTok KOL Matcher",
  description: "AI Automation Engine for Thai TikTok Influencer Discovery, Hybrid Scoring & Campaign Matching",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full bg-slate-950 text-slate-100">
      <body className="min-h-full flex flex-col font-sans antialiased selection:bg-rose-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}

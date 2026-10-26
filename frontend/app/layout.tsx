import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Convert Cake — Thai TikTok KOL Performance Matcher",
  description: "Performance-driven TikTok Influencer Intelligence & Anti-Spam Matching Engine for Thai Brands by Convert Cake",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="th" className="h-full bg-slate-50 text-slate-900">
      <body className="min-h-full flex flex-col font-sans antialiased selection:bg-[#0536d2] selection:text-white">
        {children}
      </body>
    </html>
  );
}

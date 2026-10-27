import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { SidebarNav } from "../components/SidebarNav";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "ChurnGuardAI | E-Commerce Churn Prevention Ops",
  description: "AI-powered customer churn detection, explainable risk scores, and human-in-the-loop retention offer workflow.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full bg-paper text-ink font-sans flex flex-col md:flex-row antialiased">
        <SidebarNav />
        <main className="flex-1 md:pl-64 min-h-screen flex flex-col">
          <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full flex-1">
            {children}
          </div>
        </main>
      </body>
    </html>
  );
}

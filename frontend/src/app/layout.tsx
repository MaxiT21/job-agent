import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Playfair_Display } from "next/font/google";

import { DemoBanner } from "@/components/DemoBanner";
import { Nav } from "@/components/Nav";
import { isDemo } from "@/lib/agent";

import "./globals.css";

const playfair = Playfair_Display({ variable: "--font-playfair", subsets: ["latin"] });
const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const jetbrains = JetBrains_Mono({ variable: "--font-jetbrains", subsets: ["latin"] });

export const metadata: Metadata = {
  title: isDemo ? "Job Agent — demo" : "Job Agent",
  description:
    "An AI agent that tailors a CV and cover letter to a job posting without inventing experience.",
  robots: isDemo ? undefined : { index: false, follow: false },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${playfair.variable} ${inter.variable} ${jetbrains.variable} antialiased`}
    >
      <body className="min-h-screen font-sans">
        {isDemo && <DemoBanner />}
        <Nav />
        <main className="mx-auto w-full max-w-5xl px-4 pb-24 pt-8 sm:px-6">{children}</main>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "hipoclipse - AI-First Marketing Automation",
  description: "Orchestrate complex global campaigns with autonomous neural engines.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}

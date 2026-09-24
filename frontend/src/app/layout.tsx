import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import ScrollObserver from "@/components/ScrollObserver";
import { AuthProvider } from "@/context/AuthContext";
import { BrandProvider } from "@/context/BrandContext";
import AuthModal from "@/components/auth/AuthModal";

const plusJakartaSans = Plus_Jakarta_Sans({
  variable: "--font-jakarta",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Hipoclipse | Intelligent sales platform with agents",
  description:
    "Hipoclipse helps large enterprises improve customer relationships and increase omnichannel sales with AI agents.",
  icons: {
    icon: "/images/favicon.png",
    shortcut: "/images/favicon.png",
    apple: "/images/favicon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${plusJakartaSans.variable} antialiased bg-[#0e151c]`}
    >
      <body
        suppressHydrationWarning
        className="min-h-screen w-full m-0 p-0 bg-[#0e151c] text-[#f3f4f6] flex flex-col selection:bg-[#20b8e5]/30 selection:text-white"
      >
        <AuthProvider>
          <BrandProvider>
            <ScrollObserver />
            <AuthModal />
            {children}
          </BrandProvider>
        </AuthProvider>
      </body>
    </html>
  );
}

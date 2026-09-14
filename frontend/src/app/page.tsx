import Navbar from "@/components/Navbar";
import HeroSection from "@/components/HeroSection";
import BrandTicker from "@/components/BrandTicker";
import PlatformOverview from "@/components/PlatformOverview";
import SalesAgentSection from "@/components/SalesAgentSection";
import SecuritySection from "@/components/SecuritySection";
import CTASection from "@/components/CTASection";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <div className="page-wrapper min-h-screen selection:bg-[#d75dff]/30 selection:text-[#0e151c]">
      {/* Top Floating Navbar */}
      <Navbar />

      {/* Hero Section with 24px rounded dark card, dots grid, and Lottie animation */}
      <HeroSection />

      {/* Partner Brand Logos Infinite Ticker */}
      <BrandTicker />

      {/* Overview Section with Modular Platform & User Journey Graphic */}
      <PlatformOverview />

      {/* Sales Agent Section (Recreamos con AI al mejor vendedor) */}
      <SalesAgentSection />

      {/* Platform Security & AI Architecture with Lottie */}
      <SecuritySection />

      {/* Final Omnichannel CTA */}
      <CTASection />

      {/* Footer with Newsletter & Links */}
      <Footer />
    </div>
  );
}

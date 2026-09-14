import Hero from "@/components/home/Hero";
import Features from "@/components/home/Features";
import CTA from "@/components/home/CTA";

export default function Home() {
  return (
    <main className="bg-[#F8FAFC] min-h-screen">
      <Hero />
      <Features />
      <CTA />
    </main>
  );
}

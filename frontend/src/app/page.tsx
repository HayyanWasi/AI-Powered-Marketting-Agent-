"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useBrand } from "@/context/BrandContext";

export default function LandingPage() {
  const router = useRouter();
  const { user, isLoading: authLoading, setIsAuthModalOpen } = useAuth();
  const { brands, isLoading: brandsLoading, error: brandError, refreshBrands } = useBrand();

  // The navbar is transparent over the video hero, and switches to a solid
  // light bar with dark text once it scrolls over the light sections below.
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > window.innerHeight - 90);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Authenticated users should not see the public marketing landing page:
  // if they have a completed brand, route straight to /campaigns;
  // if they have no completed brand, route to /brandsetup.
  useEffect(() => {
    if (authLoading || !user || brandsLoading || brandError) return;

    const hasCompletedBrand = Array.isArray(brands) && brands.some((b) => b.is_complete === true);
    if (hasCompletedBrand) {
      router.replace("/campaigns");
    } else {
      router.replace("/brandsetup");
    }
  }, [user, authLoading, brands, brandsLoading, brandError, router]);

  // While determining destination for an authenticated user, show a minimal loading state
  if (user && !brandError) {
    return (
      <div className="min-h-screen bg-[#0b1116] flex flex-col items-center justify-center text-white">
        <Loader2 className="w-8 h-8 animate-spin text-[#1174b8] mb-3" />
        <p className="text-[14px] text-white/70">Loading workspace…</p>
      </div>
    );
  }

  // Recoverable error state if brand loading fails: do not assume 0 brands or force setup
  if (user && brandError) {
    return (
      <div className="min-h-screen bg-[#0b1116] flex flex-col items-center justify-center text-white px-4">
        <div className="max-w-md w-full bg-[#162029] border border-white/10 rounded-xl p-6 text-center shadow-lg">
          <p className="text-[16px] font-semibold text-white mb-2">Unable to load brand</p>
          <p className="text-[13px] text-white/70 mb-5">{brandError}</p>
          <div className="flex items-center justify-center gap-3">
            <button
              type="button"
              onClick={() => {
                void refreshBrands().catch(() => {});
              }}
              className="px-4 py-2 rounded-lg bg-[#1174b8] text-white text-[13.5px] font-semibold hover:bg-[#0e5f99] transition-colors cursor-pointer"
            >
              Retry
            </button>
            <button
              type="button"
              onClick={() => router.replace("/campaigns")}
              className="px-4 py-2 rounded-lg bg-white/10 text-white text-[13.5px] font-medium hover:bg-white/15 transition-colors cursor-pointer"
            >
              Go to Campaigns
            </button>
          </div>
        </div>
      </div>
    );
  }

  const linkCls = scrolled
    ? "px-3.5 py-1.5 rounded-full text-[#52606B] hover:text-[#18222D] hover:bg-[#F1F5F9] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1174b8]"
    : "px-3.5 py-1.5 rounded-full text-white/80 hover:text-white hover:bg-white/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/80";

  return (
    <div className="bg-[#0b1116] text-white">
      {/* Pill navbar: transparent over the video, solid + dark once scrolled */}
      <header className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[min(1040px,calc(100%-24px))]">
        <nav
          className={`flex items-center justify-between gap-4 rounded-full border backdrop-blur-md px-3 sm:px-5 py-2.5 transition-colors duration-300 ${
            scrolled
              ? "border-[#e6e9ec] bg-white/95 shadow-md text-[#18222D]"
              : "border-white/15 bg-white/10 shadow-lg shadow-black/20 text-white"
          }`}
        >
          {/* Left: logo and brand text */}
          <Link
            href="/"
            className="flex items-center gap-2 shrink-0 pl-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1174b8] rounded-lg"
            title="Hipoclipse"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.png" alt="Hipoclipse" className="w-7 h-7 rounded-lg object-contain" />
            <span className={`text-[15px] font-semibold tracking-tight ${scrolled ? "text-[#18222D]" : "text-white"}`}>
              Hipoclipse
            </span>
          </Link>

          {/* Middle: nav items */}
          <div className="hidden md:flex items-center gap-1 text-[13.5px] font-medium">
            <a href="#features" className={linkCls}>Features</a>
            <a href="#how" className={linkCls}>How it works</a>
            {user ? (
              <Link href="/campaigns" className={linkCls}>Campaigns</Link>
            ) : (
              <a href="#features" className={linkCls}>Capabilities</a>
            )}
          </div>

          {/* Right: CTA & Sign in */}
          <div className="flex items-center gap-2">
            {!authLoading && !user && (
              <button
                type="button"
                onClick={() => setIsAuthModalOpen(true)}
                className={`cursor-pointer ${linkCls}`}
              >
                Sign in
              </button>
            )}
            <Link
              href="/brandsetup"
              className={`shrink-0 inline-flex items-center rounded-full text-[13.5px] font-semibold px-4 py-2 border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1174b8] ${
                scrolled
                  ? "bg-[#1174b8] text-white border-[#0e5f99] hover:bg-[#0e5f99]"
                  : "bg-white text-[#0b1116] border-[#0b1116]/10 hover:bg-white/90"
              }`}
            >
              Set up brand
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero with video background */}
      <section className="relative min-h-screen flex items-center overflow-hidden">
        <video
          className="absolute inset-0 w-full h-full object-cover"
          src="/landing-bg.mp4"
          autoPlay
          muted
          loop
          playsInline
          aria-hidden="true"
        />
        {/* Legibility overlay: darker on the left where the text sits, so the
            white copy stays readable over the bright parts of the video. */}
        <div
          className="absolute inset-0"
          aria-hidden="true"
          style={{
            background:
              "linear-gradient(90deg, rgba(9,15,20,0.84) 0%, rgba(9,15,20,0.58) 45%, rgba(9,15,20,0.18) 100%), linear-gradient(180deg, rgba(9,15,20,0.35) 0%, rgba(9,15,20,0.3) 45%, rgba(9,15,20,0.7) 100%)",
          }}
        />

        <div className="relative z-10 w-full max-w-[1040px] mx-auto px-6 py-28 sm:py-32">
          <div className="max-w-[36rem]">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 border border-white/15 text-[12.5px] font-medium text-white/90 mb-5 backdrop-blur-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-[#38bdf8]" />
              <span>LinkedIn Marketing Operations</span>
            </div>
            <h1 className="text-[clamp(2.4rem,5.5vw,4.4rem)] font-bold leading-[1.08] tracking-tight">
              Run your LinkedIn on autopilot
            </h1>
            <p className="mt-5 text-[clamp(1rem,1.4vw,1.15rem)] text-white/80 leading-relaxed max-w-xl">
              Tell Hipoclipse about your brand once. It writes your posts, schedules
              them, publishes to LinkedIn, and helps you handle replies, so your
              feed keeps moving without you in it every day.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/brandsetup"
                className="inline-flex items-center rounded-full bg-white text-[#0b1116] text-[14.5px] font-semibold px-6 py-3 border border-[#0b1116]/12 hover:bg-white/90 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
              >
                Set up brand
              </Link>
              <a
                href="#how"
                className="inline-flex items-center rounded-full border border-white/25 bg-white/10 backdrop-blur-sm text-white text-[14.5px] font-medium px-6 py-3 hover:bg-white/20 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
              >
                See how it works
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="bg-[#f6f7f8] text-[#18222D] py-20 sm:py-24 px-6 border-t border-[#e6e9ec]">
        <div className="max-w-[1040px] mx-auto">
          <div className="max-w-xl mb-12">
            <p className="text-xs font-semibold text-[#1174b8] mb-1.5">
              Platform capabilities
            </p>
            <h2 className="text-[clamp(1.8rem,3vw,2.4rem)] font-bold tracking-tight text-[#18222D] leading-tight">
              Everything the agent handles for you
            </h2>
            <p className="text-[14px] text-[#52606B] mt-2 leading-relaxed">
              Designed to take over the daily mechanics of LinkedIn publishing while keeping your unique voice and strategy intact.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Feature
              badge="Content Studio"
              title="Plans & writes on-brand posts"
              body="Transforms your brand guidelines, audience profile, and proven milestones into structured weekly campaigns with posts, media prompts, and video scripts."
            />
            <Feature
              badge="LinkedIn Dispatch"
              title="Schedules & publishes directly"
              body="Connect your LinkedIn profile once. Posts are dispatched on schedule with timezone-accurate publishing and automated queue recovery."
            />
            <Feature
              badge="Engagement"
              title="Syncs & triages incoming replies"
              body="Pulls comment activity straight to your workspace so you can review and respond with consistent tone, or let autopilot triage replies."
            />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="bg-white text-[#18222D] py-20 sm:py-24 px-6 border-t border-[#e6e9ec]">
        <div className="max-w-[1040px] mx-auto">
          <div className="max-w-xl mb-14">
            <p className="text-xs font-semibold text-[#1174b8] mb-1.5">
              Workflow
            </p>
            <h2 className="text-[clamp(1.8rem,3vw,2.4rem)] font-bold tracking-tight text-[#18222D] leading-tight">
              One brand setup, complete campaign automation
            </h2>
            <p className="text-[14px] text-[#52606B] mt-2 leading-relaxed">
              A clear three-stage sequence to build momentum on LinkedIn without ongoing manual writing.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
            <Step
              stepNumber="01"
              title="Define brand parameters"
              body="Enter company goals, audience profile, and tone guardrails once. The system remembers your standards for every future campaign."
            />
            <Step
              stepNumber="02"
              title="Generate & review strategy"
              body="Review the generated content calendar, post angles, and call-to-actions. Edit anything directly before it enters the publishing pipeline."
            />
            <Step
              stepNumber="03"
              title="Publish & track engagement"
              body="Your connected LinkedIn profile receives scheduled posts automatically while inbound comment activity is monitored in real time."
            />
          </div>

          <div className="mt-14 pt-8 border-t border-[#e6e9ec] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <p className="text-[15px] font-semibold text-[#18222D]">Ready to automate your LinkedIn presence?</p>
              <p className="text-[13px] text-[#52606B]">Set up your brand profile in under three minutes.</p>
            </div>
            <Link
              href="/brandsetup"
              className="inline-flex items-center rounded-full bg-[#1174b8] text-white text-[14px] font-semibold px-6 py-2.5 border border-[#0e5f99] hover:bg-[#0e5f99] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1174b8]"
            >
              Set up brand
            </Link>
          </div>
        </div>
      </section>

      {/* Footer strip */}
      <footer className="bg-[#0b1116] text-white/70 border-t border-white/10">
        <div className="max-w-[1040px] mx-auto px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-[13px]">
          <p className="text-white/60">
            Hipoclipse · made by Hayyan Wasi · © {new Date().getFullYear()}
          </p>
          <div className="flex items-center gap-6">
            <a
              href="https://github.com/HayyanWasi"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1174b8] rounded"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                <circle cx="6" cy="6" r="2.5" />
                <circle cx="6" cy="18" r="2.5" />
                <circle cx="18" cy="8" r="2.5" />
                <path d="M6 8.5v7M18 10.5c0 3.2-3.4 3.5-6.5 3.5H6" />
              </svg>
              <span>github.com/HayyanWasi</span>
            </a>
            <a
              href="mailto:hayyanwasi360@gmail.com"
              className="inline-flex items-center gap-1.5 hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1174b8] rounded"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                <rect x="3" y="5" width="18" height="14" rx="2" />
                <path d="M3 7l9 6 9-6" />
              </svg>
              <span>hayyanwasi360@gmail.com</span>
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

function Feature({ badge, title, body }: { badge: string; title: string; body: string }) {
  return (
    <div className="rounded-[14px] border border-[#e2e8f0] bg-white p-6 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 flex flex-col justify-between">
      <div>
        <span className="inline-block text-[11px] font-semibold text-[#1174b8] bg-[#e9f2fa] px-2.5 py-1 rounded-md mb-3">
          {badge}
        </span>
        <h3 className="text-[16px] font-semibold text-[#18222D] leading-snug">{title}</h3>
        <p className="text-[13.5px] text-[#52606B] leading-relaxed mt-2">{body}</p>
      </div>
    </div>
  );
}

function Step({ stepNumber, title, body }: { stepNumber: string; title: string; body: string }) {
  return (
    <div className="flex flex-col">
      <div className="flex items-center gap-3 mb-3">
        <span className="w-8 h-8 rounded-full bg-[#EDF6F9] text-[#187CA4] text-[13px] font-bold grid place-items-center shrink-0">
          {stepNumber}
        </span>
        <div className="h-[1px] bg-[#e6e9ec] flex-1" />
      </div>
      <h3 className="text-[16px] font-semibold text-[#18222D]">{title}</h3>
      <p className="text-[13.5px] text-[#52606B] leading-relaxed mt-1.5">{body}</p>
    </div>
  );
}

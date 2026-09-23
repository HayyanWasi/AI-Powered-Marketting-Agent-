"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowRight, PenLine, Send, MessagesSquare } from "lucide-react";

export default function LandingPage() {
  // The navbar is transparent over the video hero, and switches to a solid
  // light bar with dark text once it scrolls over the light sections below.
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > window.innerHeight - 90);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const linkCls = scrolled
    ? "px-3 py-1.5 rounded-full text-[#5a6771] hover:text-[#1f2a30] hover:bg-[#f2f4f6] transition-colors"
    : "px-3 py-1.5 rounded-full text-white/80 hover:text-white hover:bg-white/10 transition-colors";

  return (
    <div className="bg-[#0b1116] text-white">
      {/* Pill navbar: transparent over the video, solid + dark once scrolled */}
      <header className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[min(1040px,calc(100%-24px))]">
        <nav
          className={`flex items-center justify-between gap-4 rounded-full border backdrop-blur-md px-3 sm:px-5 py-2.5 transition-colors duration-300 ${
            scrolled
              ? "border-[#e6e9ec] bg-white/95 shadow-md"
              : "border-white/15 bg-white/10 shadow-lg shadow-black/20"
          }`}
        >
          {/* Left: logo and brand text linking to landing page */}
          <Link href="/" className="flex items-center gap-2 shrink-0 pl-1" title="Hipoclipse">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.png" alt="Hipoclipse" className="w-7 h-7 rounded-lg object-contain" />
            <span className={`text-[15px] font-semibold tracking-tight ${scrolled ? "text-[#1f2a30]" : "text-white"}`}>
              Hipoclipse
            </span>
          </Link>

          {/* Middle: nav items */}
          <div className="hidden md:flex items-center gap-1 text-[13.5px] font-medium">
            <a href="#features" className={linkCls}>Features</a>
            <a href="#how" className={linkCls}>How it works</a>
            <Link href="/new-campaign" className={linkCls}>Product</Link>
          </div>

          {/* Right: CTA */}
          <Link
            href="/brandsetup"
            className={`shrink-0 inline-flex items-center gap-1.5 rounded-full text-[13.5px] font-semibold px-4 py-2 border transition-colors ${
              scrolled
                ? "bg-[#1174b8] text-white border-[#0e5f99] hover:bg-[#0e5f99]"
                : "bg-white text-[#0b1116] border-[#0b1116]/10 hover:bg-white/90"
            }`}
          >
            Set up your brand <ArrowRight size={15} />
          </Link>
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
              "linear-gradient(90deg, rgba(9,15,20,0.82) 0%, rgba(9,15,20,0.55) 45%, rgba(9,15,20,0.15) 100%), linear-gradient(180deg, rgba(9,15,20,0.35) 0%, rgba(9,15,20,0.3) 45%, rgba(9,15,20,0.7) 100%)",
          }}
        />

        <div className="relative z-10 w-full max-w-[1040px] mx-auto px-6">
          <div className="max-w-[34rem]">
            <p className="text-[12px] font-semibold tracking-[0.16em] uppercase text-white/70 mb-5">
              Marketing agent for LinkedIn
            </p>
            <h1 className="text-[clamp(2.4rem,6vw,4.6rem)] font-semibold leading-[1.05] tracking-tight">
              Run your LinkedIn on autopilot
            </h1>
            <p className="mt-5 text-[clamp(1rem,1.5vw,1.2rem)] text-white/80 leading-relaxed">
              Tell Hipoclipse about your brand once. It writes your posts, schedules
              them, publishes to LinkedIn, and helps you handle the replies, so your
              feed keeps moving without you in it every day.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/brandsetup"
                className="inline-flex items-center gap-2 rounded-full bg-white text-[#0b1116] text-[15px] font-semibold px-6 py-3 border border-[#0b1116]/12 hover:bg-white/90 transition-colors"
              >
                Set up your brand <ArrowRight size={17} />
              </Link>
              <a
                href="#how"
                className="inline-flex items-center rounded-full border border-white/25 bg-white/10 backdrop-blur-sm text-white text-[15px] font-medium px-6 py-3 hover:bg-white/20 transition-colors"
              >
                See how it works
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="bg-[#f6f7f8] text-[#1f2a30] py-20 sm:py-28 px-6">
        <div className="max-w-[1040px] mx-auto">
          <p className="text-[12px] font-semibold tracking-[0.14em] uppercase text-[#1174b8] mb-3">
            What it does
          </p>
          <h2 className="text-[clamp(1.8rem,3.5vw,2.6rem)] font-semibold leading-tight max-w-[20ch]">
            Everything the agent handles for you
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mt-10">
            <Feature
              icon={<PenLine size={20} />}
              title="Plans & writes"
              body="Turns your brand profile into a campaign plan, then writes on-brand posts, images, and video."
            />
            <Feature
              icon={<Send size={20} />}
              title="Schedules & publishes"
              body="Queues everything and publishes to your own connected LinkedIn account, on time."
            />
            <Feature
              icon={<MessagesSquare size={20} />}
              title="Handles replies"
              body="Syncs inbound comments so you can respond from one place, or let autopilot keep it moving."
            />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="bg-white text-[#1f2a30] py-20 sm:py-28 px-6 border-t border-[#e6e9ec]">
        <div className="max-w-[1040px] mx-auto">
          <p className="text-[12px] font-semibold tracking-[0.14em] uppercase text-[#1174b8] mb-3">
            How it works
          </p>
          <h2 className="text-[clamp(1.8rem,3.5vw,2.6rem)] font-semibold leading-tight max-w-[20ch]">
            One brand setup, a full campaign
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mt-10">
            <Step n="01" title="Set your brand" body="Company, audience, mission, and voice, captured once." />
            <Step n="02" title="Generate the campaign" body="The agent plans and writes posts in your voice." />
            <Step n="03" title="Publish & engage" body="Schedule, publish, and reply, hands-off if you want." />
          </div>
          <div className="mt-12">
            <Link
              href="/brandsetup"
              className="inline-flex items-center gap-2 rounded-full bg-[#1174b8] text-white text-[15px] font-semibold px-6 py-3 border border-[#0e5f99] hover:bg-[#0e5f99] transition-colors"
            >
              Set up your brand <ArrowRight size={17} />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer strip */}
      <footer className="bg-[#0b1116] text-white/70 border-t border-white/10">
        <div className="max-w-[1040px] mx-auto px-6 py-5 flex flex-col sm:flex-row items-center justify-between gap-3 text-[13px]">
          <p>
            Hipoclipse · made by Hayyan Wasi · © {new Date().getFullYear()}
          </p>
          <div className="flex items-center gap-5">
            <a
              href="https://github.com/HayyanWasi"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 hover:text-white transition-colors"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                <circle cx="6" cy="6" r="2.5" />
                <circle cx="6" cy="18" r="2.5" />
                <circle cx="18" cy="8" r="2.5" />
                <path d="M6 8.5v7M18 10.5c0 3.2-3.4 3.5-6.5 3.5H6" />
              </svg>
              github.com/HayyanWasi
            </a>
            <a
              href="mailto:hayyanwasi360@gmail.com"
              className="inline-flex items-center gap-1.5 hover:text-white transition-colors"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                <rect x="3" y="5" width="18" height="14" rx="2" />
                <path d="M3 7l9 6 9-6" />
              </svg>
              hayyanwasi360@gmail.com
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

function Feature({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return (
    <div className="rounded-[14px] border border-[#e6e9ec] bg-white p-6 shadow-sm">
      <span className="w-10 h-10 rounded-xl bg-[#e9f2fa] text-[#1174b8] grid place-items-center mb-4">
        {icon}
      </span>
      <h3 className="text-[16px] font-semibold">{title}</h3>
      <p className="text-[13.5px] text-[#5a6771] leading-relaxed mt-1.5">{body}</p>
    </div>
  );
}

function Step({ n, title, body }: { n: string; title: string; body: string }) {
  return (
    <div>
      <span className="text-[28px] font-semibold text-[#c4d3dc]">{n}</span>
      <h3 className="text-[16px] font-semibold mt-2">{title}</h3>
      <p className="text-[13.5px] text-[#5a6771] leading-relaxed mt-1.5">{body}</p>
    </div>
  );
}

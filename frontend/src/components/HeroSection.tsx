"use client";

import Image from "next/image";
import Link from "next/link";
import { Lottie } from "lottie-react";

export default function HeroSection() {
  return (
    <section className="relative pt-24 pb-4 overflow-hidden">
      {/* 24px Rounded Dark Hero Card */}
      <div className="rounded-[24px] bg-[#0e151c] text-white relative overflow-hidden hero-dot-pattern border border-[#272f38]/60 shadow-2xl pt-16 pb-12 sm:pt-24 sm:pb-20 px-4 sm:px-8 lg:px-12">
        {/* Background radial glow */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[500px] bg-gradient-to-tr from-[#00c2ee]/15 via-[#d75dff]/20 to-[#edae3e]/15 blur-[130px] rounded-full pointer-events-none -z-10" />

        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
            {/* Left Column: Headline & Content */}
            <div className="lg:col-span-6 flex flex-col items-start text-left z-10">
              {/* Sparkle Icon Badge with Scroll Reveal */}
              <div
                data-reveal
                data-reveal-delay="50"
                className="mb-6 flex items-center justify-center p-2 rounded-xl bg-white/5 border border-white/10 shadow-lg shadow-black/40"
              >
                <Image
                  src="/images/sparkle-icon.svg"
                  alt="AI Icon"
                  width={26}
                  height={26}
                  className="w-6 h-6 animate-pulse"
                />
              </div>

              {/* Main Headline with Scroll Reveal in English */}
              <h1
                data-reveal
                data-reveal-delay="150"
                className="text-4xl sm:text-5xl xl:text-6xl font-extrabold tracking-tight text-white leading-[1.12] mb-6"
              >
                <span>The first </span>
                <span className="text-gradient">intelligent sales platform with agents.</span>
              </h1>

              {/* Description Subtitle with Scroll Reveal in English */}
              <p
                data-reveal
                data-reveal-delay="250"
                className="text-base sm:text-lg text-[#faf8f4]/80 leading-relaxed font-normal mb-8 max-w-xl"
              >
                That help your customers grow, wherever you are: WhatsApp, app or call.
                Manage your entire customer experience with data and artificial intelligence
                that work for you.
              </p>

              {/* Action CTA with Yalo Sliding Text & Gradient Animation */}
              <div data-reveal data-reveal-delay="350">
                <Link
                  href="/contact-us"
                  className="yalo-btn yalo-btn-primary px-8 py-3.5 text-sm sm:text-base font-semibold shadow-xl"
                >
                  <div className="yalo-btn-text-wrapper">
                    <span className="yalo-btn-text">
                      Contact Us <span className="ml-1">→</span>
                    </span>
                    <span className="yalo-btn-text">
                      Contact Us <span className="ml-1">→</span>
                    </span>
                  </div>
                  <div className="yalo-btn-bg" />
                </Link>
              </div>
            </div>

            {/* Right Column: Interactive Lottie Animation with Scroll Reveal */}
            <div
              data-reveal
              data-reveal-delay="200"
              className="lg:col-span-6 relative flex items-center justify-center min-h-[360px] sm:min-h-[460px] xl:min-h-[520px]"
            >
              {/* Subtle glow behind animation */}
              <div className="absolute inset-0 bg-gradient-to-r from-[#00c2ee]/15 to-[#d75dff]/15 rounded-full blur-3xl pointer-events-none" />

              <div className="w-full max-w-[560px] h-full flex items-center justify-center relative">
                <Lottie
                  src="/lottie/hero.json"
                  loop={true}
                  autoplay={true}
                  className="w-full h-auto max-h-[520px] drop-shadow-2xl"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

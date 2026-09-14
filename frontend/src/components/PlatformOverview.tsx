"use client";

import Image from "next/image";
import Link from "next/link";

export default function PlatformOverview() {
  return (
    <section className="relative my-6 rounded-[24px] bg-[#0e151c] text-white py-20 lg:py-28 px-4 sm:px-8 lg:px-12 overflow-hidden border border-[#272f38]/60 shadow-2xl">
      {/* Background radial glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] bg-gradient-to-r from-[#d75dff]/15 via-[#00c2ee]/10 to-transparent blur-[130px] pointer-events-none" />

      <div className="max-w-6xl mx-auto text-center flex flex-col items-center relative z-10">
        {/* Pillar Badge with Scroll Reveal */}
        <div
          data-reveal
          data-reveal-delay="50"
          className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-white/5 border border-white/10 mb-6 shadow-sm"
        >
          <Image
            src="/images/sparkle-icon.svg"
            alt="Icon"
            width={18}
            height={18}
            className="w-4 h-4"
          />
          <span className="text-xs font-semibold uppercase tracking-wider text-white/90">
            Platform
          </span>
        </div>

        {/* Heading with Scroll Reveal in English */}
        <h2
          data-reveal
          data-reveal-delay="150"
          className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.15] mb-6 max-w-4xl"
        >
          <span className="text-gradient">Everything</span> your customers need,{" "}
          <span className="text-gradient">in one place</span>
        </h2>

        {/* Subtitle with Scroll Reveal in English */}
        <p
          data-reveal
          data-reveal-delay="250"
          className="text-base sm:text-lg text-white/75 max-w-2xl leading-relaxed mb-8"
        >
          Manage your customers&apos; journey with a modular platform that personalizes every
          interaction with data and AI.
        </p>

        {/* CTA Button with Yalo Sliding Text Animation */}
        <div data-reveal data-reveal-delay="350" className="mb-14">
          <Link
            href="/platform"
            className="yalo-btn yalo-btn-primary px-7 py-3 text-sm font-semibold shadow-xl"
          >
            <div className="yalo-btn-text-wrapper">
              <span className="yalo-btn-text">
                Get to know the platform <span className="ml-1">→</span>
              </span>
              <span className="yalo-btn-text">
                Get to know the platform <span className="ml-1">→</span>
              </span>
            </div>
            <div className="yalo-btn-bg" />
          </Link>
        </div>

        {/* User Journey Graphic with Scroll Reveal */}
        <div
          data-reveal
          data-reveal-delay="200"
          className="w-full relative rounded-2xl overflow-hidden shadow-2xl border border-[#272f38] bg-[#0e151c] p-2 sm:p-4 hover:border-[#d75dff]/40 transition-colors duration-500"
        >
          <Image
            src="/images/user-journey.webp"
            alt="Hipoclipse Platform Architecture & Intelligence Hub"
            width={1024}
            height={571}
            className="w-full h-auto rounded-xl object-contain"
            priority
          />
        </div>
      </div>
    </section>
  );
}

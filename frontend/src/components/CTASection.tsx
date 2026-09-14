"use client";

import Link from "next/link";

export default function CTASection() {
  return (
    <section className="relative my-6 px-0 overflow-hidden">
      <div
        data-reveal
        data-reveal-delay="100"
        className="max-w-6xl mx-auto rounded-[24px] p-10 sm:p-20 text-center relative overflow-hidden border border-[#272f38] shadow-2xl bg-[#0e151c]"
        style={{
          backgroundImage: "url('/images/cta-bg.webp')",
          backgroundPosition: "center",
          backgroundSize: "cover",
        }}
      >
        <div className="absolute inset-0 bg-[#0e151c]/65 backdrop-blur-[2px]" />

        <div className="relative z-10 max-w-3xl mx-auto flex flex-col items-center">
          <h2 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-tight mb-6">
            Optimize your <span className="text-gradient">omnichannel strategy</span>
          </h2>

          <p className="text-base sm:text-xl text-white/80 font-normal leading-relaxed mb-10 max-w-2xl">
            With intelligent agents and transforms every interaction into an opportunity.
          </p>

          <Link
            href="/platform"
            className="yalo-btn yalo-btn-primary px-9 py-4 text-base font-semibold shadow-2xl"
          >
            <div className="yalo-btn-text-wrapper">
              <span className="yalo-btn-text">
                Discover How <span className="ml-1">→</span>
              </span>
              <span className="yalo-btn-text">
                Discover How <span className="ml-1">→</span>
              </span>
            </div>
            <div className="yalo-btn-bg" />
          </Link>
        </div>
      </div>
    </section>
  );
}

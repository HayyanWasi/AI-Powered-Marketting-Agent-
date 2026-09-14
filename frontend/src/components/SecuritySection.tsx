"use client";

import Image from "next/image";
import Link from "next/link";
import { Lottie } from "lottie-react";

export default function SecuritySection() {
  return (
    <section className="relative my-6 rounded-[24px] bg-[#0e151c] text-white py-20 lg:py-24 px-4 sm:px-8 lg:px-12 overflow-hidden border border-[#272f38]/60 shadow-2xl">
      <div className="max-w-6xl mx-auto text-center flex flex-col items-center">
        {/* Badge with Scroll Reveal */}
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
          className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.15] mb-6 max-w-3xl"
        >
          The <span className="text-gradient">smart and safe</span> way to sell
        </h2>

        {/* Description with Scroll Reveal in English */}
        <p
          data-reveal
          data-reveal-delay="250"
          className="text-base sm:text-lg text-[#faf8f4]/80 max-w-3xl leading-relaxed mb-8"
        >
          Our intelligent sales platform combines AI, automation and virtual agents to empower
          your teams, strengthen your customer relationships and generate real results, in a
          secure environment, with a world-class architecture designed to protect your business
          and its privacy.
        </p>

        {/* CTA with Yalo Sliding Text Animation in English */}
        <div data-reveal data-reveal-delay="350" className="mb-14">
          <Link
            href="/platform"
            className="yalo-btn yalo-btn-primary px-8 py-3 text-sm font-semibold shadow-xl"
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

        {/* Security Lottie Animation Graphic with Scroll Reveal */}
        <div
          data-reveal
          data-reveal-delay="200"
          className="w-full max-w-4xl relative rounded-3xl overflow-hidden border border-[#272f38] bg-[#141b24]/80 p-4 sm:p-8 shadow-2xl flex items-center justify-center min-h-[350px] hover:border-[#363b42] transition-colors"
        >
          <Lottie
            src="/lottie/security.json"
            loop={true}
            autoplay={true}
            className="w-full h-auto max-h-[500px]"
          />
        </div>
      </div>
    </section>
  );
}

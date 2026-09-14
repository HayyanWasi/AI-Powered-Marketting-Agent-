"use client";

import Image from "next/image";
import Link from "next/link";

const metrics = [
  {
    icon: "/images/metric-icon-1.svg",
    number: "3X",
    description: "Conversion than a traditional e-commerce site",
  },
  {
    icon: "/images/metric-icon-2.svg",
    number: "+40%",
    description: "Average ticket",
  },
  {
    icon: "/images/metric-icon-3.svg",
    number: "+49%",
    description: "In SKUs per order",
  },
];

export default function SalesAgentSection() {
  return (
    <section className="relative my-6 rounded-[24px] bg-[#0e151c] text-white py-20 lg:py-24 px-4 sm:px-8 lg:px-12 overflow-hidden border border-[#272f38]/60 shadow-2xl">
      {/* Background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-gradient-to-r from-[#d75dff]/15 via-[#00c2ee]/10 to-transparent blur-[120px] pointer-events-none" />

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
            Sales agent
          </span>
        </div>

        {/* Heading with Scroll Reveal in English */}
        <h2
          data-reveal
          data-reveal-delay="150"
          className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.15] mb-5"
        >
          We recreate with AI <br />
          <span className="text-gradient">the best seller</span>
        </h2>

        {/* Subtitle with Scroll Reveal in English */}
        <p
          data-reveal
          data-reveal-delay="250"
          className="text-base sm:text-lg text-[#faf8f4]/80 mb-8 max-w-xl"
        >
          Artificial intelligence. Real results.
        </p>

        {/* Button with Yalo Sliding Text Animation in English */}
        <div data-reveal data-reveal-delay="350" className="mb-16">
          <Link
            href="/oris"
            className="yalo-btn yalo-btn-primary px-8 py-3 text-sm font-semibold shadow-xl"
          >
            <div className="yalo-btn-text-wrapper">
              <span className="yalo-btn-text">
                Meet Oris <span className="ml-1">→</span>
              </span>
              <span className="yalo-btn-text">
                Meet Oris <span className="ml-1">→</span>
              </span>
            </div>
            <div className="yalo-btn-bg" />
          </Link>
        </div>

        {/* 3 Metric Cards with Staggered Scroll Reveal in English */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full">
          {metrics.map((metric, index) => (
            <div
              key={index}
              data-reveal
              data-reveal-delay={`${150 + index * 100}`}
              className="relative p-8 rounded-2xl bg-[#141b24]/90 border border-[#272f38] text-left flex flex-col items-start hover:border-[#363b42] transition-all duration-300 hover:shadow-2xl hover:shadow-[#00c2ee]/10 hover:-translate-y-1.5 group"
            >
              <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <Image
                  src={metric.icon}
                  alt="Metric Icon"
                  width={24}
                  height={24}
                  className="w-6 h-6"
                />
              </div>

              <div className="text-5xl sm:text-6xl font-black text-gradient mb-3 tracking-tight">
                {metric.number}
              </div>

              <p className="text-base text-white/80 font-normal leading-snug">
                {metric.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

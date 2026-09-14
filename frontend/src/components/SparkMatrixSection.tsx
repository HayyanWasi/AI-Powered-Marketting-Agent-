"use client";

import Image from "next/image";

export default function SparkMatrixSection() {
  return (
    <section className="relative my-6 rounded-[24px] bg-[#0e151c] text-white py-16 sm:py-20 px-4 sm:px-8 lg:px-12 overflow-hidden border border-[#272f38]/60 shadow-2xl">
      <div className="max-w-5xl mx-auto">
        <div
          data-reveal
          data-reveal-delay="100"
          className="rounded-3xl bg-[#141b24] border border-[#272f38] p-8 sm:p-14 flex flex-col md:flex-row items-center justify-between gap-10 shadow-2xl relative overflow-hidden"
        >
          {/* Subtle background glow */}
          <div className="absolute -right-20 -bottom-20 w-80 h-80 bg-[#d75dff]/15 rounded-full blur-3xl pointer-events-none" />

          {/* Left Text in English */}
          <div className="flex-1 text-left z-10">
            <h3 className="text-2xl sm:text-4xl font-extrabold text-white leading-tight mb-4">
              Recognized by SPARK Matrix as Leader in{" "}
              <span className="text-gradient">Conversational Commerce</span>
            </h3>

            <p className="text-base text-white/75 leading-relaxed max-w-xl">
              This recognition positions Hipoclipse among the most advanced platforms in the world,
              thanks to its AI-first architecture and its ability to offer consistent,
              connected interactions across all channels.
            </p>
          </div>

          {/* Right Badge Image */}
          <div className="flex-shrink-0 flex items-center justify-center p-3 bg-white rounded-2xl shadow-xl z-10 hover:scale-105 transition-transform duration-300">
            <Image
              src="/images/spark-badge.png"
              alt="SPARK Matrix Leader Badge"
              width={200}
              height={200}
              className="w-40 sm:w-48 h-auto object-contain"
              unoptimized
            />
          </div>
        </div>
      </div>
    </section>
  );
}

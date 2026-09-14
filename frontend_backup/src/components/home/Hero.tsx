'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import styles from './Hero.module.css';

const slides = [
  {
    image: '/image1.png',
    caption: '1-Click Orchestration',
    subtitle: 'Automated multi-platform campaign execution',
  },
  {
    image: '/image2.png',
    caption: 'Brand DNA Memory',
    subtitle: 'Contextual brand tone & voice synthesis',
  },
  {
    image: '/image3.png',
    caption: '100% Autopilot ROI',
    subtitle: 'Real-time performance tuning & analytics',
  },
];

export default function Hero() {
  const [activeSlide, setActiveSlide] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveSlide((prev) => (prev + 1) % slides.length);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  return (
    <section className="min-h-[85vh] flex items-center justify-center bg-[#F8FAFC] px-4 sm:px-8 lg:px-16 py-16 relative overflow-hidden">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-center w-full max-w-6xl mx-auto">

        {/* Left Column: Headline, Subheadline & CTAs (Spans 6 Columns) */}
        <div className="lg:col-span-6 flex flex-col justify-center space-y-6 z-10 pl-2 lg:pl-6">

          {/* Main Headline */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-slate-900 leading-[1.1] tracking-tight">
            AI-First Marketing <br />
            <span className="text-[#33D9B2] inline-block">
              Automation
            </span>
          </h1>

          {/* Subheadline */}
          <p className="text-lg sm:text-xl text-slate-600 font-medium leading-relaxed max-w-xl">
            Eliminate multi-channel marketing chaos. Hipoclipse&apos;s autonomous neural engine crafts, schedules, and optimizes hyper-targeted campaigns with 100% brand voice fidelity.
          </p>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-4 pt-4">
            <Link href="/dashboard">
              <button className={styles.primaryBtn}>
                <span>Start Free Trial</span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
              </button>
            </Link>
            <Link href="#docs">
              <button className={styles.secondaryBtn}>
                Book Demo
              </button>
            </Link>
          </div>

        </div>

        {/* Right Column: Image Carousel (Spans 6 Columns) */}
        <div className="lg:col-span-6 flex flex-col items-center z-10 w-full mt-8 lg:mt-0">

          {/* Carousel Card Container (Borderless & Shadowless) */}
          <div className="relative overflow-hidden rounded-3xl w-full max-w-xl aspect-[4/3]">
            {slides.map((slide, index) => (
              <div
                key={index}
                className={`absolute inset-0 transition-opacity duration-700 ease-in-out ${index === activeSlide ? 'opacity-100 z-10 pointer-events-auto' : 'opacity-0 z-0 pointer-events-none'
                  }`}
              >
                <img
                  src={slide.image}
                  alt={slide.caption}
                  className="w-full h-full object-cover rounded-3xl"
                />

                {/* Spaciously Heights Caption Overlay */}
                <div className="absolute bottom-6 left-6 right-6 bg-slate-900/85 backdrop-blur-md rounded-2xl px-6 py-4 text-white z-20 flex items-center justify-between min-h-[58px] border border-white/10">
                  <div className="flex items-center gap-3">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#33D9B2] animate-pulse shrink-0" />
                    <span className="font-extrabold text-white text-base sm:text-lg tracking-wide">{slide.caption}</span>
                  </div>
                  <span className="text-xs sm:text-sm text-slate-300 font-medium hidden sm:inline ml-3">{slide.subtitle}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Centralized Carousel Pagination Dots */}
          <div className="mt-6 flex justify-center items-center gap-2">
            {slides.map((_, index) => (
              <button
                key={index}
                onClick={() => setActiveSlide(index)}
                aria-label={`Go to slide ${index + 1}`}
                className={`transition-all duration-300 cursor-pointer ${index === activeSlide
                  ? 'bg-[#33D9B2] w-8 h-2.5 rounded-full'
                  : 'bg-slate-300 w-2.5 h-2.5 rounded-full hover:bg-slate-400'
                  }`}
              />
            ))}
          </div>

        </div>

      </div>
    </section>
  );
}

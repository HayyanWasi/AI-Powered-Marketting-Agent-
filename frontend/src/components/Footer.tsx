"use client";

import { useState } from "react";
import Link from "next/link";

export default function Footer() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) {
      setSubmitted(true);
      setEmail("");
    }
  };

  return (
    <footer
      className="relative my-8 rounded-[24px] overflow-hidden border border-[#272f38]/60 shadow-2xl bg-black"
      style={{
        backgroundImage: "url('/images/footer-galaxy-bg.png')",
        backgroundPosition: "center",
        backgroundSize: "cover",
        backgroundRepeat: "no-repeat",
      }}
    >
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-16 sm:py-20 flex flex-col items-center text-center space-y-8">
        {/* Logo: hipoclipse */}
        <Link href="/" className="inline-block hover:opacity-90 transition-opacity">
          <span className="text-[34px] sm:text-[42px] font-black tracking-tight text-white lowercase select-none">
            hipoclipse
          </span>
        </Link>

        {/* Navigation Links */}
        <nav className="flex flex-wrap items-center justify-center gap-6 sm:gap-10 text-[15px] sm:text-base font-normal text-white/90">
          <Link href="/" className="hover:text-white transition-colors">
            Platform
          </Link>
          <Link href="/dashboard" className="hover:text-white transition-colors">
            Dashboard
          </Link>
          <Link href="/brandsetup" className="hover:text-white transition-colors">
            Brandsetup
          </Link>
          <Link href="/new-campaign" className="hover:text-white transition-colors">
            New Campaign
          </Link>
          <Link href="/video-generation" className="hover:text-white transition-colors">
            Video Generation
          </Link>
          <Link href="/prospects" className="hover:text-white transition-colors">
            Prospects
          </Link>
          <Link href="/history" className="hover:text-white transition-colors">
            History
          </Link>
        </nav>

        {/* Newsletter Section */}
        <div className="flex flex-col items-center text-center w-full pt-1">
          <p className="text-sm sm:text-[15px] font-normal text-white mb-3">
            Subscribe to our newsletter
          </p>

          {submitted ? (
            <div className="flex items-center justify-center space-x-2 text-emerald-400 py-2.5 text-sm font-medium">
              <span>Thank you for subscribing!</span>
            </div>
          ) : (
            <form
              onSubmit={handleSubmit}
              className="flex items-center justify-center gap-3 w-full max-w-md"
            >
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full sm:w-[320px] h-[40px] px-3.5 rounded-[8px] bg-white text-[#0e151c] text-sm focus:outline-none focus:ring-2 focus:ring-[#4364F7] shadow-sm"
              />
              <button
                type="submit"
                className="h-[40px] px-6 rounded-[8px] bg-[#4364F7] hover:bg-[#3253eb] text-white text-sm font-semibold transition-colors cursor-pointer shadow-sm flex items-center justify-center flex-shrink-0"
              >
                Submit
              </button>
            </form>
          )}
        </div>

        {/* Copyright */}
        <div className="text-xs sm:text-[13px] text-white/80 font-normal pt-2">
          Copyright © {new Date().getFullYear()} Hipoclipse | All Rights Reserved
        </div>

        {/* Legal Links */}
        <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3 text-xs sm:text-[13px] text-white/80">
          <Link href="/terms-and-conditions" className="hover:text-white transition-colors">
            Terms and conditions
          </Link>
          <span className="text-white/40">|</span>
          <Link href="/privacy-policy" className="hover:text-white transition-colors">
            Privacy Policy
          </Link>
          <span className="text-white/40">|</span>
          <Link href="/security" className="hover:text-white transition-colors">
            Security
          </Link>
          <span className="text-white/40">|</span>
          <a
            href="https://www.bloomrdesign.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-white transition-colors"
          >
            Web credits
          </a>
        </div>

        {/* Social Icons (White circular buttons with dark icons) */}
        <div className="flex items-center justify-center space-x-3 pt-0.5">
          <a
            href="https://www.youtube.com"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="YouTube"
            className="w-7 h-7 rounded-full bg-white hover:opacity-90 flex items-center justify-center text-black transition-opacity shadow-sm"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
              <path d="M19.6069 6.99482C19.5307 6.69695 19.3152 6.47221 19.0684 6.40288C18.6299 6.28062 16.501 6 12.001 6C7.50098 6 5.37252 6.28073 4.93225 6.40323C4.68776 6.47123 4.4723 6.69593 4.3951 6.99482C4.2863 7.41923 4.00098 9.19595 4.00098 12C4.00098 14.804 4.2863 16.5808 4.3954 17.0064C4.47126 17.3031 4.68676 17.5278 4.93251 17.5968C5.37252 17.7193 7.50098 18 12.001 18C16.501 18 18.6299 17.7194 19.0697 17.5968C19.3142 17.5288 19.5297 17.3041 19.6069 17.0052C19.7157 16.5808 20.001 14.8 20.001 12C20.001 9.2 19.7157 7.41923 19.6069 6.99482ZM10.001 15.5V8.5L16.001 12L10.001 15.5Z" />
            </svg>
          </a>
          <a
            href="https://www.linkedin.com"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="LinkedIn"
            className="w-7 h-7 rounded-full bg-white hover:opacity-90 flex items-center justify-center text-black transition-opacity shadow-sm"
          >
            <svg viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5">
              <path d="M4.6269 3.3333C4.62666 3.87617 4.2973 4.36469 3.79414 4.5685C3.29098 4.77231 2.7145 4.65071 2.33652 4.26104C1.95854 3.87137 1.85455 3.29144 2.07359 2.79472C2.29263 2.298 2.79095 1.98368 3.33357 1.99996C4.05428 2.0216 4.62723 2.61226 4.6269 3.3333ZM4.6669 5.6533H2.00024V13.9999H4.6669V5.6533ZM8.88025 5.6533H6.2269V13.9999H8.85359V9.61994C8.85359 7.17994 12.0336 6.95328 12.0336 9.61994V13.9999H14.6669V8.71328C14.6669 4.59996 9.96025 4.7533 8.85359 6.77328L8.88025 5.6533Z" />
            </svg>
          </a>
        </div>
      </div>
    </footer>
  );
}

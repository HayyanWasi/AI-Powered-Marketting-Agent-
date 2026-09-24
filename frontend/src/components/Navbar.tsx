"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export default function Navbar() {
  const { user, setIsAuthModalOpen, signOut } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 15) {
        setScrolled(true);
      } else {
        setScrolled(false);
      }
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 px-3 sm:px-6 lg:px-[45.6px] pt-2.5 transition-all duration-300">
      <nav
        className={`max-w-[1429.57px] mx-auto h-[80px] rounded-[16px] px-6 sm:px-8 lg:px-[45.6px] transition-all duration-300 flex items-center justify-between bg-[#0e151c] border border-[#272f38]/60 ${scrolled
            ? "shadow-2xl shadow-black/60 border-[#363b42]"
            : "shadow-xl shadow-black/30"
          }`}
      >
        {/* Logo: hipoclipse */}
        <Link href="/" className="flex items-center space-x-2.5 flex-shrink-0 group">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.png" alt="Hipoclipse" className="w-8 h-8 rounded-lg object-contain transition-transform group-hover:scale-105 duration-200" />
          <span className="text-[25px] sm:text-[27px] font-black tracking-tight text-white lowercase select-none transition-transform group-hover:scale-105 duration-200">
            hipoclipse
          </span>
        </Link>

        {/* Desktop Nav Links: Campaigns, brandsetup, new campaign, video generation, history */}
        <div className="hidden lg:flex items-center space-x-6 xl:space-x-8">

          <Link
            href="/campaigns"
            className="text-[15px] text-[#faf8f4] hover:text-white font-medium transition-colors"
          >
            Campaigns
          </Link>

          <Link
            href="/brandsetup"
            className="text-[15px] text-[#faf8f4] hover:text-white font-medium transition-colors"
          >
            Brandsetup
          </Link>

          <Link
            href="/new-campaign"
            className="text-[15px] text-[#faf8f4] hover:text-white font-medium transition-colors"
          >
            New Campaign
          </Link>

          <Link
            href="/video-generation"
            className="text-[15px] text-[#faf8f4] hover:text-white font-medium transition-colors"
          >
            Video Generation
          </Link>

          <Link
            href="/prospects"
            className="text-[15px] text-[#faf8f4] hover:text-white font-medium transition-colors"
          >
            Prospects
          </Link>

          <Link
            href="/history"
            className="text-[15px] text-[#faf8f4] hover:text-white font-medium transition-colors"
          >
            History
          </Link>
        </div>

        {/* Right CTA and Action Buttons */}
        <div className="hidden sm:flex items-center space-x-3">
          {/* Dynamic Authentication Controls */}
          {user ? (
            <div className="flex items-center space-x-2">
              <div className="h-[40px] px-3.5 py-2 text-xs font-medium text-white bg-[#151D26] border border-[#273240] rounded-[8px] flex items-center space-x-2">
                <div className="w-5 h-5 rounded-full bg-gradient-to-tr from-[#00c2ee] to-[#d75dff] text-black font-bold text-[10px] flex items-center justify-center">
                  {(user.email?.[0] || "U").toUpperCase()}
                </div>
                <span className="truncate max-w-[120px]">{user.email?.split("@")[0]}</span>
              </div>
              <button
                type="button"
                onClick={() => signOut()}
                className="h-[40px] px-3 py-2 text-xs font-medium text-[#9AA6B2] hover:text-white hover:bg-[#1E2732] border border-[#273240] rounded-[8px] transition-all cursor-pointer"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setIsAuthModalOpen(true)}
              className="h-[40px] px-4 py-2 text-[14px] font-semibold text-[#0e151c] bg-gradient-to-r from-[#00c2ee] to-[#d75dff] hover:opacity-90 rounded-[8px] transition-all shadow-md flex items-center justify-center cursor-pointer"
            >
              Sign In
            </button>
          )}

          {/* Button 2: EN Language Switcher */}
          <div className="h-[40px] px-3.5 bg-white/10 text-white font-medium text-[13px] rounded-[8px] border border-white/10 shadow-sm flex items-center justify-center cursor-pointer select-none">
            EN
          </div>
        </div>

        {/* Mobile Menu Toggle Button */}
        <div className="flex sm:hidden items-center space-x-2">
          <Link
            href="/contact-us"
            className="px-3 py-1.5 text-xs font-semibold text-[#0e151c] bg-white rounded-[6px]"
          >
            Contact
          </Link>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 text-white/90 hover:text-white hover:bg-white/5 rounded-lg transition-colors cursor-pointer"
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </nav>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden mt-2 mx-auto max-w-[1429.57px] rounded-[16px] bg-[#0e151c]/98 border border-[#272f38] p-5 shadow-2xl backdrop-blur-2xl animate-in fade-in slide-in-from-top-3 duration-300">
          <div className="flex flex-col space-y-3">

            <Link
              href="/campaigns"
              onClick={() => setMobileMenuOpen(false)}
              className="px-3 py-2 text-base text-white/90 hover:text-white hover:bg-white/5 rounded-lg font-medium"
            >
              Campaigns
            </Link>

            <Link
              href="/brandsetup"
              onClick={() => setMobileMenuOpen(false)}
              className="px-3 py-2 text-base text-white/90 hover:text-white hover:bg-white/5 rounded-lg font-medium"
            >
              Brandsetup
            </Link>

            <Link
              href="/new-campaign"
              onClick={() => setMobileMenuOpen(false)}
              className="px-3 py-2 text-base text-white/90 hover:text-white hover:bg-white/5 rounded-lg font-medium"
            >
              New Campaign
            </Link>

            <Link
              href="/video-generation"
              onClick={() => setMobileMenuOpen(false)}
              className="px-3 py-2 text-base text-white/90 hover:text-white hover:bg-white/5 rounded-lg font-medium"
            >
              Video Generation
            </Link>

            <Link
              href="/prospects"
              onClick={() => setMobileMenuOpen(false)}
              className="px-3 py-2 text-base text-white/90 hover:text-white hover:bg-white/5 rounded-lg font-medium"
            >
              Prospects
            </Link>

            <Link
              href="/history"
              onClick={() => setMobileMenuOpen(false)}
              className="px-3 py-2 text-base text-white/90 hover:text-white hover:bg-white/5 rounded-lg font-medium"
            >
              History
            </Link>

            <div className="border-t border-[#272f38] pt-4 flex flex-col space-y-3">
              <a
                href="https://platform.hipoclipse.com/auth/login"
                target="_blank"
                rel="noopener noreferrer"
                className="w-full text-center py-2.5 text-sm font-semibold text-black bg-[#faf8f4] hover:bg-white rounded-[8px] transition-colors"
              >
                Get Started
              </a>
              <Link
                href="/contact-us"
                onClick={() => setMobileMenuOpen(false)}
                className="w-full text-center py-2.5 text-sm font-semibold text-white bg-[#0e151c] border border-[#45484d] rounded-[8px] hover:bg-[#1a232d] transition-colors"
              >
                Contact Us
              </Link>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

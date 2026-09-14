"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { X } from "lucide-react";

interface CaseStudy {
  id: string;
  tabLabel: string;
  tabLogo: string;
  tabLogoWidth: number;
  poster: string;
  youtubeId?: string;
  quote: string;
  author: string;
  title: string;
  link: string;
}

const caseStudies: CaseStudy[] = [
  {
    id: "femsa",
    tabLabel: "Coca-Cola FEMSA",
    tabLogo: "/images/tab-femsa.svg",
    tabLogoWidth: 89,
    poster: "/images/femsa-poster.jpg",
    youtubeId: "61949Np4QRQ",
    quote:
      "“With Hipoclipse, we have transformed our business by digitizing more than 1 million tienditas and making it easier for 600,000 to send orders monthly, primarily via WhatsApp. Scaling has never been easier.”",
    author: "Bruno Juanes",
    title: "Chief Commercial Development Officer at Coca-Cola FEMSA",
    link: "/case-studies",
  },
  {
    id: "nestle",
    tabLabel: "Nestlé",
    tabLogo: "/images/tab-nestle.svg",
    tabLogoWidth: 120,
    poster: "/images/video-nestle.webp",
    quote:
      "“Hipoclipse's product recommendation model enabled us to increase average order value by 5.3% in just one month, demonstrating the impact of conversational commerce on revenue growth.”",
    author: "Nestlé Mexico",
    title: "Chief Commercial Development Officer at Nestlé",
    link: "/case-studies",
  },
  {
    id: "mondelez",
    tabLabel: "Mondelēz",
    tabLogo: "/images/tab-mondelez.svg",
    tabLogoWidth: 95,
    poster: "/images/video-mondelez.webp",
    youtubeId: "ldaT0BxsG90",
    quote:
      "“We showed our sales team that Hipoclipse is not a one-off initiative and used them as a strategic resource to implement innovation, instead of merely taking orders at each store.”",
    author: "Leonardo Pires",
    title: "Head of B2B E-Commerce at Mondelez Brazil",
    link: "/case-studies",
  },
  {
    id: "yupi",
    tabLabel: "Yupi",
    tabLogo: "/images/tab-yupi.svg",
    tabLogoWidth: 55,
    poster: "/images/yupi-poster.jpg",
    youtubeId: "EPT2fxcYCNU",
    quote:
      "“Direct and immediate communication drives higher sales, order volume, and coverage quality. Hipoclipse stays one step ahead in technology, creating stronger connections between business and corner stores.”",
    author: "Jose F. Castro",
    title: "National Sales Manager at Yupi",
    link: "/case-studies",
  },
];

export default function CaseStudiesVideoSection() {
  const [activeTab, setActiveTab] = useState<string>("femsa");
  const [activeVideoUrl, setActiveVideoUrl] = useState<string | null>(null);

  const current = caseStudies.find((c) => c.id === activeTab) || caseStudies[0];

  const handlePlay = () => {
    if (current.youtubeId) {
      setActiveVideoUrl(`https://www.youtube.com/embed/${current.youtubeId}?autoplay=1`);
    }
  };

  return (
    <section className="relative my-6 rounded-[24px] bg-[#0e151c] text-white py-20 lg:py-24 px-4 sm:px-8 lg:px-12 overflow-hidden border border-[#272f38]/60 shadow-2xl">
      <div className="max-w-6xl mx-auto">
        {/* Tabs navigation with Scroll Reveal */}
        <div
          data-reveal
          data-reveal-delay="50"
          className="flex flex-wrap items-center justify-center gap-3 sm:gap-6 mb-12 border-b border-[#272f38] pb-6"
        >
          {caseStudies.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`relative px-5 py-3 rounded-xl transition-all duration-300 flex items-center justify-center cursor-pointer ${
                activeTab === item.id
                  ? "bg-white/10 border border-white/20 shadow-lg"
                  : "bg-white/5 border border-transparent hover:bg-white/10 opacity-70 hover:opacity-100"
              }`}
            >
              <Image
                src={item.tabLogo}
                alt={item.tabLabel}
                width={item.tabLogoWidth}
                height={30}
                className="h-6 sm:h-7 w-auto object-contain filter brightness-0 invert"
              />
              {activeTab === item.id && (
                <div className="absolute -bottom-[25px] left-0 right-0 h-0.5 bg-gradient-to-r from-[#00c2ee] via-[#d75dff] to-[#edae3e]" />
              )}
            </button>
          ))}
        </div>

        {/* Tab content panel with Scroll Reveal */}
        <div
          data-reveal
          data-reveal-delay="150"
          className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center rounded-3xl bg-[#141b24] border border-[#272f38] p-6 sm:p-10 shadow-2xl"
        >
          {/* Video Thumbnail with Play button */}
          <div className="lg:col-span-7 relative group rounded-2xl overflow-hidden aspect-video bg-black/60 shadow-xl">
            <Image
              src={current.poster}
              alt={current.author}
              fill
              className="object-cover group-hover:scale-105 transition-transform duration-500"
              unoptimized
            />
            <div className="absolute inset-0 bg-black/30 group-hover:bg-black/20 transition-colors" />

            {/* Play Button */}
            {current.youtubeId && (
              <button
                onClick={handlePlay}
                className="absolute inset-0 m-auto w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-white/20 hover:bg-white/30 backdrop-blur-md border border-white/40 flex items-center justify-center transition-all duration-300 hover:scale-110 shadow-2xl group/btn cursor-pointer"
                aria-label="Play video"
              >
                <Image
                  src="/images/play.svg"
                  alt="Play"
                  width={30}
                  height={30}
                  className="w-6 h-6 sm:w-8 sm:h-8 ml-1 filter brightness-0 invert"
                />
              </button>
            )}
          </div>

          {/* Testimonial Quote & Info */}
          <div className="lg:col-span-5 flex flex-col items-start text-left">
            <p className="text-lg sm:text-xl font-normal text-white/90 leading-relaxed mb-6 italic">
              {current.quote}
            </p>

            <div className="w-12 h-0.5 bg-gradient-to-r from-[#00c2ee] to-[#d75dff] mb-4" />

            <h4 className="text-lg font-bold text-white mb-1">{current.author}</h4>
            <p className="text-sm text-white/60 mb-8 leading-snug">{current.title}</p>

            <Link
              href={current.link}
              className="yalo-btn yalo-btn-primary px-6 py-2.5 text-sm font-semibold shadow-lg"
            >
              <div className="yalo-btn-text-wrapper">
                <span className="yalo-btn-text">
                  See More <span className="ml-1">→</span>
                </span>
                <span className="yalo-btn-text">
                  See More <span className="ml-1">→</span>
                </span>
              </div>
              <div className="yalo-btn-bg" />
            </Link>
          </div>
        </div>
      </div>

      {/* Video Lightbox Modal */}
      {activeVideoUrl && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-md p-4 animate-in fade-in duration-200">
          <div className="relative w-full max-w-4xl aspect-video rounded-2xl overflow-hidden shadow-2xl border border-white/20">
            <button
              onClick={() => setActiveVideoUrl(null)}
              className="absolute top-4 right-4 z-10 p-2 rounded-full bg-black/70 hover:bg-black text-white/80 hover:text-white transition-colors cursor-pointer"
              aria-label="Close video"
            >
              <X size={24} />
            </button>
            <iframe
              src={activeVideoUrl}
              title="Customer Story Video"
              className="w-full h-full"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
        </div>
      )}
    </section>
  );
}

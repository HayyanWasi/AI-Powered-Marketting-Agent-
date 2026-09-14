"use client";

import Image from "next/image";
import Link from "next/link";

const articles = [
  {
    image: "/images/blog1.png",
    category: "Hipoclipse Blog",
    title:
      "How artificial intelligence is changing the game for global bottlers",
    date: "September 3, 2025",
    link: "/blog/ia-para-embotelladoras",
    isExternal: false,
  },
  {
    image: "/images/blog2.png",
    category: "Success Stories",
    title:
      "Coca-Cola HBC increases average order value by 20% with intelligent sales agents on WhatsApp",
    date: "January 6, 2026",
    link: "/case-studies",
    isExternal: false,
  },
  {
    image: "/images/blog3.webp",
    category: "Articles and News",
    title: "Startup that blends shopping and texting on Whatsapp Lands $50M",
    date: "July 15, 2025",
    link: "https://www.wsj.com/articles/startup-that-blends-shopping-and-texting-on-whatsapp-lands-50-million-11622019600?page=1",
    isExternal: true,
  },
];

export default function BlogSection() {
  return (
    <section className="relative py-20 lg:py-28 bg-[#faf8f4] text-[#0e151c] overflow-hidden">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header Row with Scroll Reveal in English */}
        <div className="flex flex-col sm:flex-row items-start sm:items-end justify-between mb-12 gap-4">
          <div>
            <div
              data-reveal
              data-reveal-delay="50"
              className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-[#0e151c]/5 border border-[#0e151c]/10 mb-4 shadow-sm"
            >
              <Image
                src="/images/sparkle-icon.svg"
                alt="Icon"
                width={18}
                height={18}
                className="w-4 h-4 filter brightness-0"
              />
              <span className="text-xs font-semibold uppercase tracking-wider text-[#0e151c]">
                Resources
              </span>
            </div>
            <h2
              data-reveal
              data-reveal-delay="150"
              className="text-3xl sm:text-5xl font-extrabold tracking-tight text-[#0e151c]"
            >
              <span className="text-gradient">Latest News</span>
            </h2>
          </div>

          <div data-reveal data-reveal-delay="200">
            <Link
              href="/resources"
              className="yalo-btn yalo-btn-dark px-6 py-2.5 text-sm font-semibold shadow-md hover:shadow-lg"
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

        {/* 3 Blog Cards with Staggered Scroll Reveal in English */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {articles.map((item, index) => {
            const CardWrapper = item.isExternal ? "a" : Link;
            const extraProps = item.isExternal
              ? { target: "_blank", rel: "noopener noreferrer" }
              : {};

            return (
              <CardWrapper
                key={index}
                href={item.link}
                {...extraProps}
                data-reveal
                data-reveal-delay={`${150 + index * 100}`}
                className="group flex flex-col rounded-2xl bg-white border border-[#0e151c]/10 overflow-hidden shadow-sm hover:shadow-2xl transition-all duration-300 hover:-translate-y-1.5"
              >
                <div className="relative w-full h-52 overflow-hidden bg-gray-100">
                  <Image
                    src={item.image}
                    alt={item.title}
                    fill
                    className="object-cover group-hover:scale-105 transition-transform duration-500"
                    unoptimized
                  />
                </div>

                <div className="p-6 flex-1 flex flex-col justify-between">
                  <div>
                    <span className="inline-block px-3 py-1 text-xs font-semibold rounded-md bg-[#0e151c]/5 text-[#0e151c] mb-3">
                      {item.category}
                    </span>
                    <h3 className="text-lg font-bold text-[#0e151c] leading-snug group-hover:text-[#00c2ee] transition-colors line-clamp-3">
                      {item.title}
                    </h3>
                  </div>

                  <span className="text-xs text-[#0e151c]/60 font-medium mt-6">
                    {item.date}
                  </span>
                </div>
              </CardWrapper>
            );
          })}
        </div>
      </div>
    </section>
  );
}

"use client";

import Image from "next/image";

const partners = [
  { name: "Nestlé", src: "/images/nestle.svg", width: 88, height: 38 },
  { name: "Alpina", src: "/images/alpina.svg", width: 56, height: 38 },
  { name: "Coca-Cola", src: "/images/coca-cola.svg", width: 170, height: 38 },
  { name: "Heineken", src: "/images/heineken.svg", width: 62, height: 38 },
  { name: "FEMSA", src: "/images/femsa.svg", width: 44, height: 38 },
  { name: "Mondelēz", src: "/images/mondelez.svg", width: 104, height: 38 },
  { name: "PepsiCo", src: "/images/pepsico.svg", width: 104, height: 38 },
  { name: "Unilever", src: "/images/unilever.svg", width: 104, height: 38 },
];

export default function BrandTicker() {
  return (
    <section data-reveal className="relative my-4 rounded-[24px] bg-[#0e151c] border border-[#272f38]/60 py-10 overflow-hidden shadow-xl">
      {/* Side fades for smooth marquee transition */}
      <div className="absolute left-0 top-0 bottom-0 w-20 sm:w-36 bg-gradient-to-r from-[#0e151c] to-transparent z-10 pointer-events-none" />
      <div className="absolute right-0 top-0 bottom-0 w-20 sm:w-36 bg-gradient-to-l from-[#0e151c] to-transparent z-10 pointer-events-none" />

      <div className="ticker-track flex items-center space-x-12 sm:space-x-20">
        {/* Set 1 */}
        {partners.map((partner, index) => (
          <div
            key={`ticker-1-${index}`}
            className="flex-shrink-0 flex items-center justify-center opacity-70 hover:opacity-100 transition-opacity duration-300 filter brightness-100 hover:brightness-125 cursor-pointer"
          >
            <Image
              src={partner.src}
              alt={partner.name}
              width={partner.width}
              height={partner.height}
              className="h-7 sm:h-9 w-auto object-contain"
            />
          </div>
        ))}

        {/* Set 2 for seamless loop */}
        {partners.map((partner, index) => (
          <div
            key={`ticker-2-${index}`}
            className="flex-shrink-0 flex items-center justify-center opacity-70 hover:opacity-100 transition-opacity duration-300 filter brightness-100 hover:brightness-125 cursor-pointer"
          >
            <Image
              src={partner.src}
              alt={partner.name}
              width={partner.width}
              height={partner.height}
              className="h-7 sm:h-9 w-auto object-contain"
            />
          </div>
        ))}
      </div>
    </section>
  );
}

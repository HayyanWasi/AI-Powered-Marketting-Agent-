"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { ChevronLeft, ChevronRight } from "lucide-react";

const testimonials = [
  {
    name: "Mariel",
    quote: "“Personalized attention, thank you for your time.”",
    avatar: "/images/avatar1.webp",
  },
  {
    name: "Lucas",
    quote:
      "“Very good communication with the team and great response time from the support team.”",
    avatar: "/images/avatar2.webp",
  },
  {
    name: "Mario",
    quote:
      "“It is a complete tool, democratized and executed correctly, that generates positive impacts on Marketing and Sales.”",
    avatar: "/images/avatar3.webp",
  },
  {
    name: "Daniela",
    quote:
      "“A very attentive team with a strong commitment to customers, always ready to support us in solving day-to-day challenges.”",
    avatar: "/images/avatar4.webp",
  },
  {
    name: "Evandro",
    quote:
      "“Hipoclipse is an extremely professional company, with trained professionals always willing to help.”",
    avatar: "/images/avatar5.webp",
  },
  {
    name: "Mariana",
    quote:
      "“They are an excellent team, very agile in responding to business needs.”",
    avatar: "/images/avatar6.webp",
  },
  {
    name: "Ricardo",
    quote: "“The experience has been super good.”",
    avatar: "/images/avatar7.webp",
  },
  {
    name: "Christian",
    quote: "“Great service and communication!”",
    avatar: "/images/avatar8.webp",
  },
];

const stats = [
  {
    number: "+4 B",
    title: "In transactions",
    desc: "Companies rely on our platform to automate sales.",
    image: "/images/stat1.webp",
  },
  {
    number: "+40",
    title: "Country presence",
    desc: "We connect companies with clients in LATAM, Africa and Europe.",
    image: "/images/stat2.webp",
  },
  {
    number: "+4.4 M",
    title: "Active stores",
    desc: "We help scale relationships and transform businesses.",
    image: "/images/stat3.webp",
  },
  {
    number: "+12%",
    title: "Increase in sales",
    desc: "Our technology optimizes and enhances business growth.",
    image: "/images/stat4.webp",
  },
  {
    number: "Millions",
    title: "USD in loans placed",
    desc: "In the financial industry in Latin America.",
    image: "/images/stat5.webp",
  },
];

export default function TestimonialsSection() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [statIndex, setStatIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % testimonials.length);
    }, 5500);
    return () => clearInterval(timer);
  }, []);

  const prevTestimonial = () => {
    setCurrentIndex(
      (prev) => (prev - 1 + testimonials.length) % testimonials.length
    );
  };

  const nextTestimonial = () => {
    setCurrentIndex((prev) => (prev + 1) % testimonials.length);
  };

  const prevStat = () => {
    setStatIndex((prev) => Math.max(0, prev - 1));
  };

  const nextStat = () => {
    setStatIndex((prev) => Math.min(stats.length - 1, prev + 1));
  };

  return (
    <section className="relative py-20 lg:py-28 bg-[#faf8f4] text-[#0e151c] overflow-hidden">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center flex flex-col items-center">
        {/* Badge with Scroll Reveal */}
        <div
          data-reveal
          data-reveal-delay="50"
          className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-[#0e151c]/5 border border-[#0e151c]/10 mb-6 shadow-sm"
        >
          <Image
            src="/images/sparkle-icon.svg"
            alt="Icon"
            width={18}
            height={18}
            className="w-4 h-4 filter brightness-0"
          />
          <span className="text-xs font-semibold uppercase tracking-wider text-[#0e151c]">
            The voices of customers
          </span>
        </div>

        {/* Heading with Scroll Reveal in English */}
        <h2
          data-reveal
          data-reveal-delay="150"
          className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-[#0e151c] leading-[1.15] mb-14 max-w-4xl"
        >
          Our results{" "}
          <span className="text-gradient">speak for themselves through </span>
          our customers
        </h2>

        {/* Testimonial Quotes Carousel with Scroll Reveal */}
        <div
          data-reveal
          data-reveal-delay="250"
          className="relative w-full max-w-3xl min-h-[260px] sm:min-h-[220px] flex flex-col items-center justify-center mb-10 bg-white/60 backdrop-blur-sm border border-[#0e151c]/10 rounded-3xl p-6 sm:p-10 shadow-lg"
        >
          <div
            key={currentIndex}
            className="flex flex-col items-center animate-in fade-in zoom-in-95 duration-500 text-center"
          >
            <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full overflow-hidden border-2 border-[#d75dff]/70 p-1 mb-5 shadow-lg shadow-[#d75dff]/20 bg-white flex items-center justify-center">
              <Image
                src={testimonials[currentIndex].avatar}
                alt={testimonials[currentIndex].name}
                width={70}
                height={70}
                className="object-contain w-full h-full"
                unoptimized
              />
            </div>

            <p className="text-xl sm:text-2xl font-medium text-[#0e151c] max-w-2xl leading-relaxed mb-4 italic">
              {testimonials[currentIndex].quote}
            </p>

            <span className="text-sm font-bold tracking-wider uppercase text-[#00c2ee]">
              {testimonials[currentIndex].name}
            </span>
          </div>

          {/* Carousel Arrows */}
          <div className="flex items-center space-x-3 mt-8">
            <button
              onClick={prevTestimonial}
              className="p-2.5 rounded-full border border-[#0e151c]/15 bg-white text-[#0e151c] hover:bg-[#0e151c] hover:text-white transition-colors cursor-pointer shadow-sm"
              aria-label="Previous quote"
            >
              <ChevronLeft size={18} />
            </button>
            <div className="flex space-x-1.5">
              {testimonials.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentIndex(i)}
                  className={`h-2 rounded-full transition-all duration-300 cursor-pointer ${
                    i === currentIndex ? "w-6 bg-[#d75dff]" : "w-2 bg-[#0e151c]/20"
                  }`}
                  aria-label={`Go to slide ${i + 1}`}
                />
              ))}
            </div>
            <button
              onClick={nextTestimonial}
              className="p-2.5 rounded-full border border-[#0e151c]/15 bg-white text-[#0e151c] hover:bg-[#0e151c] hover:text-white transition-colors cursor-pointer shadow-sm"
              aria-label="Next quote"
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>

        {/* Global Impact Stats Grid with Staggered Scroll Reveal */}
        <div className="w-full mt-14 pt-14 border-t border-[#0e151c]/10">
          <div className="flex items-center justify-between mb-8">
            <h3
              data-reveal
              data-reveal-delay="100"
              className="text-xl sm:text-3xl font-extrabold text-[#0e151c] text-left"
            >
              Impact on a global scale
            </h3>
            <div className="hidden sm:flex items-center space-x-2">
              <button
                onClick={prevStat}
                disabled={statIndex === 0}
                className="p-2 rounded-full border border-[#0e151c]/15 bg-white disabled:opacity-30 text-[#0e151c] hover:bg-[#0e151c] hover:text-white transition-colors cursor-pointer shadow-sm"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                onClick={nextStat}
                disabled={statIndex >= stats.length - 3}
                className="p-2 rounded-full border border-[#0e151c]/15 bg-white disabled:opacity-30 text-[#0e151c] hover:bg-[#0e151c] hover:text-white transition-colors cursor-pointer shadow-sm"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-5 text-left">
            {stats.map((stat, i) => (
              <div
                key={i}
                data-reveal
                data-reveal-delay={`${100 + i * 80}`}
                className="relative rounded-2xl bg-white border border-[#0e151c]/10 p-5 flex flex-col justify-between hover:border-[#0e151c]/25 transition-all duration-300 hover:shadow-xl hover:-translate-y-1.5 group shadow-sm"
              >
                <div className="relative w-full h-36 rounded-xl overflow-hidden mb-4 bg-gray-100">
                  <Image
                    src={stat.image}
                    alt={stat.title}
                    width={378}
                    height={200}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    unoptimized
                  />
                </div>

                <div>
                  <div className="text-3xl font-black text-gradient mb-1 tracking-tight">
                    {stat.number}
                  </div>
                  <div className="text-sm font-bold text-[#0e151c] mb-2">
                    {stat.title}
                  </div>
                  <p className="text-xs text-[#0e151c]/70 leading-relaxed">
                    {stat.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

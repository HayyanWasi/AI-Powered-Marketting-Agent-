"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";

export default function ScrollObserver() {
  const pathname = usePathname();

  useEffect(() => {
    // Check if user prefers reduced motion
    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const revealAll = () => {
      document.querySelectorAll("[data-reveal]").forEach((el) => {
        el.classList.add("is-revealed");
      });
    };

    if (prefersReducedMotion) {
      revealAll();
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-revealed");
            observer.unobserve(entry.target);
          }
        });
      },
      {
        threshold: 0.05,
        rootMargin: "60px 0px 60px 0px",
      }
    );

    const checkAndObserve = () => {
      const elements = document.querySelectorAll("[data-reveal]:not(.is-revealed)");
      const viewportHeight = window.innerHeight || 800;

      elements.forEach((el) => {
        const rect = el.getBoundingClientRect();
        // If element is already in or near viewport, reveal immediately
        if (rect.top < viewportHeight + 120 && rect.bottom > -100) {
          el.classList.add("is-revealed");
        } else {
          observer.observe(el);
        }
      });
    };

    // Execute immediately on route change
    checkAndObserve();

    // Check again after browser layout render ticks
    const rafId = requestAnimationFrame(checkAndObserve);
    const timer1 = setTimeout(checkAndObserve, 80);
    const timer2 = setTimeout(checkAndObserve, 350);

    // Watch for dynamic DOM updates and route transitions
    const mutationObserver = new MutationObserver(() => {
      checkAndObserve();
    });

    mutationObserver.observe(document.body, {
      childList: true,
      subtree: true,
    });

    return () => {
      cancelAnimationFrame(rafId);
      clearTimeout(timer1);
      clearTimeout(timer2);
      observer.disconnect();
      mutationObserver.disconnect();
    };
  }, [pathname]);

  return null;
}

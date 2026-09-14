'use client';

import { useEffect, useRef } from 'react';
import styles from './Features.module.css';
import Image from 'next/image';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

if (typeof window !== 'undefined') {
  gsap.registerPlugin(ScrollTrigger);
}

export default function Features() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const topCards = [
      containerRef.current.querySelector(`.${styles.cardBrand}`),
      containerRef.current.querySelector(`.${styles.cardSpeed}`),
    ].filter(Boolean);

    const bottomCards = [
      containerRef.current.querySelector(`.${styles.cardDistribution}`),
      containerRef.current.querySelector(`.${styles.cardPreview}`),
    ].filter(Boolean);

    // Initial Fade-In & Entrance Elevation
    gsap.fromTo(
      [...topCards, ...bottomCards],
      {
        opacity: 0,
        y: 40,
      },
      {
        opacity: 1,
        y: 0,
        duration: 0.8,
        stagger: 0.14,
        ease: 'power3.out',
      }
    );

    // Top Row: Scroll-Driven Parallax LEFT (x: 0 -> -80px)
    if (topCards.length > 0) {
      gsap.to(topCards, {
        x: -80,
        ease: 'none',
        scrollTrigger: {
          trigger: containerRef.current,
          start: 'top 85%',
          end: 'bottom 15%',
          scrub: 1,
        },
      });
    }

    // Bottom Row: Scroll-Driven Parallax RIGHT (x: 0 -> 80px)
    if (bottomCards.length > 0) {
      gsap.to(bottomCards, {
        x: 80,
        ease: 'none',
        scrollTrigger: {
          trigger: containerRef.current,
          start: 'top 85%',
          end: 'bottom 15%',
          scrub: 1,
        },
      });
    }

    return () => {
      ScrollTrigger.getAll().forEach((trigger) => trigger.kill());
    };
  }, []);

  return (
    <section className={`section ${styles.features}`} id="features">
      <div className={`container`} ref={containerRef}>
        {/* Section Header */}
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Engineered for Infinite Scale</h2>
          <p className={styles.sectionSubtitle}>
            Built on specialized multi-modal models trained exclusively for viral engagement and brand consistency.
          </p>
        </div>

        {/* Asymmetric Bento Grid Layout */}
        <div className={styles.bentoGrid}>

          {/* Card 1: Train on your brand (Col 1 to 7) - TOP ROW */}
          <div className={styles.cardBrand}>
            <div className={styles.cardTop}>
              <div className={styles.iconContainer}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2a8 8 0 0 0-8 8c0 1.5.5 2.8 1.3 4L4 21l3-1.4c1.5.9 3.2 1.4 5 1.4a8 8 0 0 0 8-8 8 8 0 0 0-8-8z" />
                  <circle cx="12" cy="10" r="3" />
                </svg>
              </div>
              <h3 className={styles.cardTitle}>Train on your brand</h3>
              <p className={styles.cardText}>
                Our proprietary neural networks ingest your existing assets to perfectly mimic your brand's unique semantic signature and visual identity.
              </p>
            </div>

            <div className={styles.cardFooter}>
              <span className={styles.footerTag}>Semantic Mirroring Tech</span>
              <span className={styles.footerArrow}>&rarr;</span>
            </div>
          </div>

          {/* Card 2: AI Content Generation (Col 8 to 12) - TOP ROW */}
          <div className={styles.cardSpeed}>
            <div className={styles.cardTop}>
              <div className={styles.iconContainer}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z" />
                </svg>
              </div>
              <h3 className={styles.cardTitle}>AI Content Generation</h3>
              <p className={styles.cardText}>
                Produce high-fidelity copy and bespoke creative assets in seconds. High-end aesthetic defaults built-in.
              </p>
            </div>

            <div className={styles.speedWidget}>
              <div className={styles.speedLabels}>
                <span className={styles.speedLabel}>GENERATION SPEED</span>
                <span className={styles.speedValue}>0.4s</span>
              </div>
              <div className={styles.progressBar}>
                <div className={styles.progressFill} />
              </div>
            </div>
          </div>

          {/* Card 3: Multi-platform posting (Col 1 to 5) - BOTTOM ROW */}
          <div className={styles.cardDistribution}>
            <div className={styles.cardTop}>
              <div className={styles.iconContainer}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.65 1.65 0 0 0 .11 1.85 1.65 1.65 0 0 0 1.95.42M4.6 9a1.65 1.65 0 0 0-.11-1.85 1.65 1.65 0 0 0-1.95-.42M15 4.6a1.65 1.65 0 0 0-1.85-.11 1.65 1.65 0 0 0-.42-1.95M9 19.4a1.65 1.65 0 0 0 1.85.11 1.65 1.65 0 0 0 .42 1.95M12 2v2M12 20v2M5 5l1.5 1.5M17.5 17.5 19 19M2 12h2M20 12h2M5 19l1.5-1.5M17.5 6.5 19 5" />
                </svg>
              </div>
              <h3 className={styles.cardTitle}>Multi-platform posting</h3>
              <p className={styles.cardText}>
                Seamless distribution across every major API. One command to deploy worldwide across social, web, and ads.
              </p>
            </div>

            <div className={styles.channelsList}>
              <span className={styles.channelChip}>LinkedIn</span>
              <span className={styles.channelChip}>Instagram</span>
              <span className={styles.channelChip}>Meta</span>
              <span className={styles.channelChip}>YouTube</span>
            </div>
          </div>

          {/* Card 4: Styled Media Asset Preview Container (Col 6 to 12) - BOTTOM ROW */}
          <div className={styles.cardPreview}>
            {/* Window Top Navigation Bar */}
            <div className={styles.windowHeader}>
              <div className={styles.windowDots}>
                <span className={styles.dotClose} />
                <span className={styles.dotMin} />
                <span className={styles.dotMax} />
              </div>
              <div className={styles.windowTitle}>neural_engine_cluster.png</div>
              <div className={styles.windowBadge}>
                <span className={styles.pulseDot} />
                LIVE STREAM
              </div>
            </div>

            {/* Window Content Image Frame */}
            <div className={styles.previewFrame}>
              <Image
                src="/server_room.png"
                alt="Neural Engine Cluster Infrastructure"
                fill
                className={styles.previewImage}
                priority
              />
              <div className={styles.imageOverlaySheen} />
            </div>
          </div>

        </div>
      </div>
    </section>
  );
}

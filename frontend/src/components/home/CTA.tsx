import Button from '../ui/Button';
import Link from 'next/link';
import styles from './CTA.module.css';

export default function CTA() {
  return (
    <section className={`section ${styles.ctaSection}`}>
      <div className={`container`}>
        <div className={styles.bannerCard}>
          {/* Ambient Background Radial Sheen */}
          <div className={styles.bannerGlow} />

          {/* Decorative Top Right Sparkle Icon */}
          <div className={styles.iconTopRight}>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z"/>
            </svg>
          </div>

          {/* Content */}
          <div className={styles.bannerContent}>
            <h2 className={styles.title}>Ready to automate the future?</h2>
            <p className={styles.subtitle}>
              Join global enterprises orchestrating their brand narrative with autonomous neural intelligence.
            </p>
            <div className={styles.buttonGroup}>
              <Link href="/dashboard">
                <Button variant="primary">Start Free Trial &rarr;</Button>
              </Link>
              <Link href="#docs">
                <Button variant="secondary">Schedule Demo</Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

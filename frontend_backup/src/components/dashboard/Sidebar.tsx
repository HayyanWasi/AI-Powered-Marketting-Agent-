"use client";
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import Button from '../ui/Button';
import styles from './Sidebar.module.css';

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className={styles.sidebar}>
      {/* Sidebar Header with Brand Mark */}
      <div className={styles.header}>
        <Link href="/" className={styles.logoLink}>
          <div className={styles.logoBadge}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z" />
            </svg>
          </div>
          <div className={styles.logoTextWrapper}>
            <span className={styles.logoText}>hipoclipse<span className={styles.logoDot}>.</span></span>
            <span className={styles.slogan}>Neural Campaign Engine</span>
          </div>
        </Link>
      </div>

      {/* Main Navigation */}
      <nav className={styles.nav}>
        <div className={styles.navSectionLabel}>NAVIGATION</div>
        <Link href="/dashboard" className={`${styles.navItem} ${pathname === '/dashboard' ? styles.active : ''}`}>
          <div className={styles.icon}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /></svg>
          </div>
          <span>Dashboard</span>
        </Link>

        <Link href="/dashboard/brand-setup" className={`${styles.navItem} ${pathname === '/dashboard/brand-setup' ? styles.active : ''}`}>
          <div className={styles.icon}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z" /></svg>
          </div>
          <span>Brand Setup</span>
        </Link>

        <Link href="/dashboard/new-campaign" className={`${styles.navItem} ${pathname.startsWith('/dashboard/new-campaign') ? styles.active : ''}`}>
          <div className={styles.icon}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="16" /><line x1="8" y1="12" x2="16" y2="12" /></svg>
          </div>
          <span>New Campaign</span>
        </Link>

        <Link href="/dashboard/video-generator" className={`${styles.navItem} ${pathname.startsWith('/dashboard/video-generator') ? styles.active : ''}`}>
          <div className={styles.icon}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18" /><line x1="7" y1="2" x2="7" y2="22" /><line x1="17" y1="2" x2="17" y2="22" /><line x1="2" y1="12" x2="22" y2="12" /><line x1="2" y1="7" x2="7" y2="7" /><line x1="2" y1="17" x2="7" y2="17" /><line x1="17" y1="17" x2="22" y2="17" /><line x1="17" y1="7" x2="22" y2="7" /></svg>
          </div>
          <span>Video Generator</span>
        </Link>

        <Link href="/dashboard/history" className={`${styles.navItem} ${pathname === '/dashboard/history' ? styles.active : ''}`}>
          <div className={styles.icon}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
          </div>
          <span>Campaign History</span>
        </Link>
      </nav>

      {/* Sidebar Footer */}
      <div className={styles.footer}>
        <Link href="/dashboard/new-campaign" className={styles.launchBtnWrapper}>
          <Button variant="primary" className={styles.launchBtn}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2l.5-.5a5.4 5.4 0 0 0 1 1l.5.5c1.5 1.5 5 2 5 2s-.5-3.74-2-5l-.5-.5a5.4 5.4 0 0 0 1-1l.5-.5c1.5-1.5 2-5 2-5s-3.74.5-5 2l-.5.5a5.4 5.4 0 0 0-1 1l-.5.5c-1.5-1.5-5-2-5-2s.5 3.74 2 5l.5.5a5.4 5.4 0 0 0-1 1l-.5.5Z" /><path d="m12 15 3.5 3.5" /><path d="M9 12 5.5 8.5" /></svg>
            LAUNCH ENGINE
          </Button>
        </Link>

        <div className={styles.footerLinks}>
          <Link href="/dashboard/settings" className={styles.footerLink}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .11 1.85 1.65 1.65 0 0 0 1.95.42M4.6 9a1.65 1.65 0 0 0-.11-1.85 1.65 1.65 0 0 0-1.95-.42M15 4.6a1.65 1.65 0 0 0-1.85-.11 1.65 1.65 0 0 0-.42-1.95M9 19.4a1.65 1.65 0 0 0 1.85.11 1.65 1.65 0 0 0 .42 1.95M12 2v2M12 20v2M5 5l1.5 1.5M17.5 17.5 19 19M2 12h2M20 12h2M5 19l1.5-1.5M17.5 6.5 19 5" /></svg>
            Settings
          </Link>
          <Link href="/dashboard/support" className={styles.footerLink}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>
            Support
          </Link>
        </div>
      </div>
    </aside>
  );
}

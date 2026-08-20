'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import Button from '@/components/ui/Button';
import styles from './page.module.css';
import { campaignApi, healthApi } from '@/lib/api';
import gsap from 'gsap';

export default function DashboardHome() {
  const [totalCampaigns, setTotalCampaigns] = useState<number | null>(null);
  const [serverOk, setServerOk] = useState<boolean | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const loadStats = async () => {
      try {
        await healthApi.check();
        setServerOk(true);
      } catch {
        setServerOk(false);
      }

      try {
        const result = await campaignApi.list({ page: 1, page_size: 1 });
        setTotalCampaigns(result.total);
      } catch {
        setTotalCampaigns(0);
      }
    };

    loadStats();
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;

    const statCards = containerRef.current.querySelectorAll(`.${styles.statsRow} > div`);
    const workflowCards = containerRef.current.querySelectorAll(`.${styles.workflowGrid} > a`);

    gsap.fromTo(
      statCards,
      { opacity: 0, y: 20 },
      { opacity: 1, y: 0, duration: 0.6, stagger: 0.08, ease: 'power2.out' }
    );

    gsap.fromTo(
      workflowCards,
      { opacity: 0, y: 20 },
      { opacity: 1, y: 0, duration: 0.6, stagger: 0.1, delay: 0.2, ease: 'power2.out' }
    );
  }, []);

  return (
    <div className={styles.dashboardContainer} ref={containerRef}>
      
      {/* 1. Header Banner & Welcome Section */}
      <div className={styles.dashboardHeader}>
        <div>
          <div className={styles.headerBadge}>
            <span className={styles.badgePulse} />
            AETHER NEURAL ENGINE READY
          </div>
          <h1 className={styles.title}>Welcome back, Creator</h1>
          <p className={styles.subtitle}>
            Your autonomous marketing engine is synchronized and ready to orchestrate global campaigns.
          </p>
        </div>

        <div className={styles.headerActions}>
          <Link href="/dashboard/brand-setup">
            <Button variant="secondary">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z"/></svg>
              Brand Memory
            </Button>
          </Link>
          <Link href="/dashboard/new-campaign">
            <Button variant="primary">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Create Campaign
            </Button>
          </Link>
        </div>
      </div>

      {/* 2. Top Metric / Analytics Row (4 Stat Cards) */}
      <div className={styles.statsRow}>
        
        {/* Stat Card 1: Active Campaigns (Mint Tint) */}
        <div className={`${styles.statCard} ${styles.cardMint}`}>
          <div className={styles.statCardHeader}>
            <span className={styles.statLabel}>Active Campaigns</span>
            <div className={styles.statIconBadge}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
            </div>
          </div>
          <div className={styles.statValueRow}>
            <span className={styles.statNumber}>{totalCampaigns ?? 0}</span>
            <span className={styles.statTrendGreen}>+12% vs last mo</span>
          </div>
          <p className={styles.statSubtext}>3 running in pipeline</p>
        </div>

        {/* Stat Card 2: AI Generations (Ice Cyan) */}
        <div className={`${styles.statCard} ${styles.cardCyan}`}>
          <div className={styles.statCardHeader}>
            <span className={styles.statLabel}>Total AI Generations</span>
            <div className={styles.statIconBadge}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z"/></svg>
            </div>
          </div>
          <div className={styles.statValueRow}>
            <span className={styles.statNumber}>1,284</span>
            <span className={styles.statTag}>0.4s avg</span>
          </div>
          <div className={styles.miniProgressBar}>
            <div className={styles.miniProgressFill} style={{ width: '78%' }} />
          </div>
        </div>

        {/* Stat Card 3: Brand Voice Status (Soft Rose Coral) */}
        <div className={`${styles.statCard} ${styles.cardRose}`}>
          <div className={styles.statCardHeader}>
            <span className={styles.statLabel}>Brand Voice Memory</span>
            <div className={styles.statIconBadge}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            </div>
          </div>
          <div className={styles.statValueRow}>
            <span className={styles.statTextHighlight}>TechFlow AI</span>
            <span className={styles.statusBadgeSynced}>SYNCHRONIZED</span>
          </div>
          <p className={styles.statSubtext}>4 reference assets registered</p>
        </div>

        {/* Stat Card 4: System Latency (Sky Cyan Blue) */}
        <div className={`${styles.statCard} ${styles.cardSky}`}>
          <div className={styles.statCardHeader}>
            <span className={styles.statLabel}>System Capacity &amp; Health</span>
            <div className={styles.statIconBadge}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            </div>
          </div>
          <div className={styles.statValueRow}>
            <span className={styles.statNumber}>42ms</span>
            <span className={serverOk ? styles.statusBadgeOnline : styles.statusBadgeOffline}>
              {serverOk ? 'BACKEND ONLINE' : 'OFFLINE'}
            </span>
          </div>
          <p className={styles.statSubtext}>99.9% Uptime guarantee</p>
        </div>

      </div>

      {/* 3. Main Workflow Section (2-Column Layout) */}
      <div className={styles.mainGrid}>
        
        {/* Left Column (2/3 Width): Quick Launch + Recent Activity */}
        <div className={styles.leftColumn}>
          
          {/* Quick Launch Workflows */}
          <div className={styles.sectionBlock}>
            <div className={styles.blockHeader}>
              <h2 className={styles.blockTitle}>Quick Launch Workflows</h2>
              <span className={styles.blockSub}>Select a module to start orchestrating</span>
            </div>

            <div className={styles.workflowGrid}>
              <Link href="/dashboard/new-campaign" className={styles.workflowCard}>
                <div className={styles.workflowIcon}>
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                </div>
                <div className={styles.workflowContent}>
                  <h3>Campaign Creation Engine</h3>
                  <p>Generate multi-platform strategy, copy &amp; image assets</p>
                </div>
                <span className={styles.workflowArrow}>&rarr;</span>
              </Link>

              <Link href="/dashboard/brand-setup" className={styles.workflowCard}>
                <div className={styles.workflowIcon}>
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z"/></svg>
                </div>
                <div className={styles.workflowContent}>
                  <h3>Brand Voice Memory</h3>
                  <p>Train neural models on your visual identity &amp; copy</p>
                </div>
                <span className={styles.workflowArrow}>&rarr;</span>
              </Link>

              <Link href="/dashboard/history" className={styles.workflowCard}>
                <div className={styles.workflowIcon}>
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                </div>
                <div className={styles.workflowContent}>
                  <h3>Campaign History Vault</h3>
                  <p>Browse, export, and re-generate past campaign runs</p>
                </div>
                <span className={styles.workflowArrow}>&rarr;</span>
              </Link>
            </div>
          </div>

          {/* Recent Campaign Activity List */}
          <div className={styles.sectionBlock}>
            <div className={styles.blockHeaderBetween}>
              <div>
                <h2 className={styles.blockTitle}>Recent Campaign Executions</h2>
                <span className={styles.blockSub}>Active drafts and generated outputs</span>
              </div>
              <Link href="/dashboard/history" className={styles.viewAllLink}>
                View All History &rarr;
              </Link>
            </div>

            <div className={styles.activityList}>
              <div className={styles.activityItem}>
                <div className={styles.activityMain}>
                  <div className={styles.activityIconCompleted}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                  </div>
                  <div>
                    <div className={styles.activityName}>Q3 AI Product Launch</div>
                    <div className={styles.activityMeta}>Channels: LinkedIn, Instagram • 6 Assets</div>
                  </div>
                </div>
                <div className={styles.activityRight}>
                  <span className={styles.chipCompleted}>COMPLETED</span>
                  <span className={styles.activityTime}>Today, 10:24 AM</span>
                </div>
              </div>

              <div className={styles.activityItem}>
                <div className={styles.activityMain}>
                  <div className={styles.activityIconGenerating}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                  </div>
                  <div>
                    <div className={styles.activityName}>Summer Growth Campaign</div>
                    <div className={styles.activityMeta}>Channels: Meta, Instagram • 4 Assets</div>
                  </div>
                </div>
                <div className={styles.activityRight}>
                  <span className={styles.chipGenerating}>GENERATING</span>
                  <span className={styles.activityTime}>12m ago</span>
                </div>
              </div>

              <div className={styles.activityItem}>
                <div className={styles.activityMain}>
                  <div className={styles.activityIconDraft}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                  </div>
                  <div>
                    <div className={styles.activityName}>Brand Re-positioning Blast</div>
                    <div className={styles.activityMeta}>Draft Setup • Target Audience Configured</div>
                  </div>
                </div>
                <div className={styles.activityRight}>
                  <span className={styles.chipDraft}>DRAFT</span>
                  <span className={styles.activityTime}>Aug 02, 2026</span>
                </div>
              </div>
            </div>
          </div>

        </div>

        {/* Right Column (1/3 Width): Neural Engine Status & System Shortcuts */}
        <div className={styles.rightColumn}>
          
          {/* Neural Engine Cluster Status Widget */}
          <div className={styles.widgetCard}>
            <div className={styles.widgetHeader}>
              <div className={styles.widgetIcon}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z"/></svg>
              </div>
              <div>
                <div className={styles.widgetTitle}>Neural Engine Cluster</div>
                <div className={styles.widgetSubtitle}>Model: Aether v2.4 Multimodal</div>
              </div>
            </div>

            <div className={styles.widgetBody}>
              <div className={styles.metricRow}>
                <span>GPU Cluster Load</span>
                <span className={styles.metricBold}>24% (Optimal)</span>
              </div>
              <div className={styles.widgetProgressBar}>
                <div className={styles.widgetProgressFill} style={{ width: '24%' }} />
              </div>

              <div className={styles.featureList}>
                <div className={styles.featureItem}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                  <span>Intent Analysis &amp; Context Building</span>
                </div>
                <div className={styles.featureItem}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                  <span>Pollinations Image Generation</span>
                </div>
                <div className={styles.featureItem}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                  <span>Semantic Brand Memory Vectoring</span>
                </div>
              </div>
            </div>
          </div>

          {/* Quick System Shortcuts */}
          <div className={styles.widgetCard}>
            <div className={styles.widgetTitle}>Quick Shortcuts</div>
            <div className={styles.shortcutsList}>
              <Link href="/dashboard/brand-setup" className={styles.shortcutItem}>
                <span>Manage Brand Reference Images</span>
                <span className={styles.shortcutArrow}>&rarr;</span>
              </Link>
              <Link href="/dashboard/history" className={styles.shortcutItem}>
                <span>Export Campaign History Logs</span>
                <span className={styles.shortcutArrow}>&rarr;</span>
              </Link>
              <Link href="#docs" className={styles.shortcutItem}>
                <span>API &amp; Platform Documentation</span>
                <span className={styles.shortcutArrow}>&rarr;</span>
              </Link>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}

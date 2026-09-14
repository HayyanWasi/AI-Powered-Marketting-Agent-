'use client';

import { useEffect, useState } from 'react';
import styles from './TopHeader.module.css';
import Image from 'next/image';
import { healthApi } from '@/lib/api';

type HealthState = 'checking' | 'healthy' | 'error';

export default function TopHeader() {
  const [serverHealth, setServerHealth] = useState<HealthState>('checking');
  const [apiReady, setApiReady] = useState<HealthState>('checking');
  const [showHealthMenu, setShowHealthMenu] = useState(false);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await healthApi.check();
        setServerHealth('healthy');
      } catch {
        setServerHealth('error');
      }

      try {
        await healthApi.ready();
        setApiReady('healthy');
      } catch {
        setApiReady('error');
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const overallState: HealthState =
    serverHealth === 'healthy' && apiReady === 'healthy'
      ? 'healthy'
      : serverHealth === 'error' || apiReady === 'error'
        ? 'error'
        : 'checking';

  const getSystemDotClass = () => {
    if (overallState === 'error') return styles.dotRed;
    if (overallState === 'checking') return styles.dotYellow;
    return styles.dotGreen;
  };

  const getSystemBadgeLabel = () => {
    if (overallState === 'error') return 'SYSTEM DEGRADED';
    if (overallState === 'checking') return 'CHECKING SYSTEMS...';
    return 'SYSTEM ONLINE';
  };

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <span className={styles.version}>AETHER V2.4</span>
        <span className={styles.separator}>|</span>

        {/* Consolidated System Health Badge */}
        <div
          className={styles.healthBadgeContainer}
          onClick={() => setShowHealthMenu(!showHealthMenu)}
        >
          <div className={styles.healthBadge}>
            <span className={getSystemDotClass()} />
            <span className={styles.healthLabel}>{getSystemBadgeLabel()}</span>
            <svg className={styles.dropdownIcon} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>

          {/* Health Popover Menu */}
          {showHealthMenu && (
            <div className={styles.healthPopover}>
              <div className={styles.healthPopoverHeader}>System Health Breakdown</div>
              <div className={styles.healthPopoverRow}>
                <span>Core Backend Server</span>
                <span className={serverHealth === 'healthy' ? styles.statusGreen : styles.statusRed}>
                  {serverHealth === 'healthy' ? 'Healthy' : 'Offline'}
                </span>
              </div>
              <div className={styles.healthPopoverRow}>
                <span>API Gateway</span>
                <span className={apiReady === 'healthy' ? styles.statusGreen : styles.statusRed}>
                  {apiReady === 'healthy' ? 'Ready' : 'Degraded'}
                </span>
              </div>
              <div className={styles.healthPopoverRow}>
                <span>Neural Inference Cluster</span>
                <span className={styles.statusGreen}>Active (42ms)</span>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className={styles.actions}>
        <button className={styles.monitoringBtn}>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><path d="M12 3l1.912 5.813a2 2 0 001.275 1.275L21 12l-5.813 1.912a2 2 0 00-1.275 1.275L12 21l-1.912-5.813a2 2 0 00-1.275-1.275L3 12l5.813-1.912a2 2 0 001.275-1.275L12 3z" /></svg>
          AI MONITORING
        </button>

        <div className={styles.iconBox} title="Toggle Theme">
          <Image src="/light_mode.png" alt="Theme Toggle" width={16} height={16} />
        </div>

        <div className={styles.iconBtn} title="Notifications">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></svg>
        </div>

        <div className={styles.iconBtn} title="Cloud Sync">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" /><polyline points="10 13 12 15 16 9" /></svg>
        </div>

        <div className={styles.profileWrapper}>
          <div className={styles.profilePic}>
            <Image src="/profile.png" alt="User Profile" width={32} height={32} />
          </div>
          <span className={styles.profileOnlineDot} />
        </div>
      </div>
    </header>
  );
}

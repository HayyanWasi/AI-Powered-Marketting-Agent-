'use client';

import { useEffect, useState } from 'react';
import styles from './page.module.css';
import Link from 'next/link';
import Button from '@/components/ui/Button';
import { campaignApi, Campaign, ApiError } from '@/lib/api';

const STATUS_DISPLAY: Record<string, string> = {
  draft: 'DRAFT',
  scheduled: 'SCHEDULED',
  active: 'ACTIVE',
  paused: 'PAUSED',
  completed: 'COMPLETED',
  archived: 'ARCHIVED',
};

const STATUS_CSS: Record<string, string> = {
  draft: 'statusDraft',
  scheduled: 'statusScheduled',
  archived: 'statusArchived',
  active: 'statusScheduled',
  completed: 'statusScheduled',
  paused: 'statusArchived',
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function CampaignHistory() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [archivingId, setArchivingId] = useState<string | null>(null);

  const PAGE_SIZE = 4;

  const loadCampaigns = async (pg: number) => {
    setLoading(true);
    setError('');
    try {
      const result = await campaignApi.list({ page: pg, page_size: PAGE_SIZE });
      setCampaigns(result.campaigns || []);
      setTotal(result.total || 0);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to connect to campaign service.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCampaigns(page);
  }, [page]);

  const handleArchive = async (id: string) => {
    setArchivingId(id);
    try {
      await campaignApi.archive(id);
      await loadCampaigns(page);
    } catch (err) {
      console.error('Archive failed:', err);
    } finally {
      setArchivingId(null);
    }
  };

  const activeCampaigns = campaigns.filter((c) => c.state === 'active' || c.state === 'scheduled').length;
  const archivedCampaigns = campaigns.filter((c) => c.state === 'archived').length;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className={styles.container}>
      <div className={styles.breadcrumbs}>WORKSPACE &gt; CAMPAIGN HISTORY</div>

      <div className={styles.headerRow}>
        <div>
          <h1 className={styles.title}>Campaign History</h1>
          <p className={styles.subtitle}>Inspect historical executions, clone draft parameters, and export campaign data.</p>
        </div>

        <Link href="/dashboard/new-campaign">
          <Button variant="primary">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            NEW CAMPAIGN
          </Button>
        </Link>
      </div>

      {/* Top 3 Metric Cards */}
      <div className={styles.statsRow}>
        
        {/* Card 1: Total Campaigns */}
        <div className={styles.statCard}>
          <div className={styles.statCardHeader}>
            <span className={styles.statTitle}>TOTAL CAMPAIGNS</span>
            <div className={styles.statIcon}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 12 12 17 22 12"/><polyline points="2 17 12 22 22 17"/></svg>
            </div>
          </div>
          <div className={styles.statValueRow}>
            <span className={styles.statValue}>{loading ? '—' : total.toLocaleString()}</span>
          </div>
          <span className={styles.statDesc}>Cumulative reach across all distribution nodes</span>
        </div>

        {/* Card 2: Active Threads */}
        <div className={styles.statCard}>
          <div className={styles.statCardHeader}>
            <span className={styles.statTitle}>ACTIVE THREADS</span>
            <div className={styles.statIcon}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><circle cx="12" cy="12" r="3"/></svg>
            </div>
          </div>
          <div className={styles.statValueRow}>
            <span className={styles.statValue}>{loading ? '—' : activeCampaigns}</span>
            <span className={styles.statLiveBadge}>
              <span className={styles.livePulseDot} />
              LIVE
            </span>
          </div>
          <span className={styles.statDesc}>Currently active or scheduled threads</span>
        </div>

        {/* Card 3: Archived */}
        <div className={styles.statCard}>
          <div className={styles.statCardHeader}>
            <span className={styles.statTitle}>ARCHIVED</span>
            <div className={styles.statIcon}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            </div>
          </div>
          <div className={styles.statValueRow}>
            <span className={styles.statValue}>{loading ? '—' : archivedCampaigns}</span>
            <span className={styles.statTagStored}>STORED</span>
          </div>
          <span className={styles.statDesc}>Completed &amp; archived campaign runs</span>
        </div>

      </div>

      {/* Main Table Card */}
      <div className={styles.tableCard}>
        <div className={styles.tableHeader}>
          <div className={styles.tableTitleRow}>
            <div className={styles.tableIcon}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
            </div>
            <h2>Past Campaigns History</h2>
          </div>

          <div className={styles.tableActions}>
            <Button variant="secondary" onClick={() => loadCampaigns(page)} className={styles.actionBtn}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              REFRESH
            </Button>
            <Button variant="secondary" className={styles.actionBtn}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              EXPORT
            </Button>
          </div>
        </div>

        {/* Content Body States */}
        {loading ? (
          <div className={styles.loadingBox}>
            <div className={styles.spinner} />
            <p>Fetching campaign history...</p>
          </div>
        ) : error ? (
          /* Styled Error Alert State Container */
          <div className={styles.errorAlertContainer}>
            <div className={styles.errorAlertHeader}>
              <div className={styles.errorAlertIcon}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              </div>
              <div>
                <h3 className={styles.errorAlertTitle}>Connection Error</h3>
                <p className={styles.errorAlertMsg}>{error}</p>
              </div>
            </div>
            <p className={styles.errorAlertGuide}>
              Please verify your backend connection or retry loading the campaign registry.
            </p>
            <Button variant="primary" onClick={() => loadCampaigns(page)} className={styles.retryBtn}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              RETRY CONNECTION
            </Button>
          </div>
        ) : campaigns.length === 0 ? (
          /* Styled Empty State Container */
          <div className={styles.emptyContainer}>
            <div className={styles.emptyIcon}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 12 12 17 22 12"/><polyline points="2 17 12 22 22 17"/></svg>
            </div>
            <h3 className={styles.emptyTitle}>No Campaigns Found</h3>
            <p className={styles.emptyText}>You have not created any campaign executions yet.</p>
            <Link href="/dashboard/new-campaign">
              <Button variant="primary">
                Create Your First Campaign
              </Button>
            </Link>
          </div>
        ) : (
          /* Campaign Table */
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>CAMPAIGN NAME</th>
                <th className={styles.th}>DATE CREATED</th>
                <th className={styles.th}>STATUS</th>
                <th className={styles.th}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map((c) => (
                <tr key={c.id} className={styles.tr}>
                  <td className={styles.td}>
                    <div className={styles.campaignInfo}>
                      <div className={styles.campaignImg}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 12 12 17 22 12"/><polyline points="2 17 12 22 22 17"/></svg>
                      </div>
                      <div>
                        <div className={styles.campaignName}>{c.name}</div>
                        <div className={styles.campaignId}>ID: {c.id.slice(0, 13)}...</div>
                      </div>
                    </div>
                  </td>
                  <td className={styles.td}>
                    <span className={styles.date}>{formatDate(c.created_at)}</span>
                  </td>
                  <td className={styles.td}>
                    <span className={`${styles.statusBadge} ${styles[STATUS_CSS[c.state] || 'statusDraft']}`}>
                      {STATUS_DISPLAY[c.state] || c.state.toUpperCase()}
                    </span>
                  </td>
                  <td className={styles.td}>
                    <div className={styles.tableActionGroup}>
                      <Link href={`/dashboard/new-campaign?campaign_id=${c.id}`}>
                        <Button variant="ghost" className={styles.tableIconBtn} title="Edit Campaign">
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                        </Button>
                      </Link>
                      {c.state === 'archived' ? (
                        <span className={styles.archivedTag}>ARCHIVED</span>
                      ) : (
                        <Button
                          variant="ghost"
                          className={styles.archiveActionBtn}
                          onClick={() => handleArchive(c.id)}
                          disabled={archivingId === c.id}
                        >
                          {archivingId === c.id ? '...' : 'Archive'}
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Pagination Bar */}
        <div className={styles.pagination}>
          <span className={styles.pageInfo}>
            Showing {((page - 1) * PAGE_SIZE) + 1}–{Math.min(page * PAGE_SIZE, total)} of {total} campaigns
          </span>
          <div className={styles.pageControls}>
            <button
              className={styles.pageBtn}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              &larr;
            </button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map((pg) => (
              <button
                key={pg}
                className={`${styles.pageBtn} ${pg === page ? styles.pageBtnActive : ''}`}
                onClick={() => setPage(pg)}
              >
                {pg}
              </button>
            ))}
            <button
              className={styles.pageBtn}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
            >
              &rarr;
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}

'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import styles from './page.module.css';
import Button from '@/components/ui/Button';
import {
  LaunchpadPreviewData,
  LinkedInPostItem,
  linkedinApi,
  videoApi,
} from '@/lib/api';

function LaunchpadContent() {
  const searchParams = useSearchParams();
  const campaignId = searchParams.get('campaign_id');

  const [activeTab, setActiveTab] = useState<'calendar' | 'video'>('calendar');
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<LaunchpadPreviewData | null>(null);
  const [launching, setLaunching] = useState(false);
  const [launched, setLaunched] = useState(false);
  const [error, setError] = useState('');
  
  // Video Generation States
  const [generatingVideo, setGeneratingVideo] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [autopilotLive, setAutopilotLive] = useState(false);

  useEffect(() => {
    if (!campaignId) return;
    const loadPreview = async () => {
      setLoading(true);
      try {
        let preview = await linkedinApi.getPreview(campaignId);
        if (!preview.posts || preview.posts.length === 0) {
          // If no posts generated yet, call AI generator automatically
          await linkedinApi.generate(campaignId).catch(() => null);
          preview = await linkedinApi.getPreview(campaignId);
        }
        setData(preview);
      } catch (err) {
        setError('Failed to load campaign preview.');
      } finally {
        setLoading(false);
      }
    };
    loadPreview();
  }, [campaignId]);

  const handleLaunch = async () => {
    if (!campaignId || launching) return;
    setLaunching(true);
    setError('');
    try {
      await linkedinApi.launch(campaignId, 'default_account');
      setLaunched(true);
    } catch (err) {
      setError('Failed to launch campaign to LinkedIn Auto-Pilot.');
    } finally {
      setLaunching(false);
    }
  };

  const handleGenerateVideo = async () => {
    if (!campaignId) return;
    setGeneratingVideo(true);
    setError('');
    try {
      const res = await videoApi.generate(campaignId);
      setVideoUrl(res.video_url);
    } catch (err: any) {
      setError(err.message || 'Failed to generate video.');
    } finally {
      setGeneratingVideo(false);
    }
  };

  const handleAutopilotLinkedIn = () => {
    setAutopilotLive(true);
  };

  if (loading) {
    return (
      <div className={styles.container} style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div style={{ color: '#10b981', fontWeight: 600 }}>Loading LinkedIn Campaign Launchpad...</div>
      </div>
    );
  }

  const posts = data?.posts || [];
  const seq = data?.outreach_sequence;
  const config = data?.autopilot_config;

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.titleGroup}>
          <h1 className={styles.title}>LinkedIn Campaign Launchpad</h1>
          <span className={`${styles.badge} ${launched ? styles.scheduled : ''}`}>
            {launched ? 'AUTO-PILOT ACTIVE' : 'DRAFT READY FOR LAUNCH'}
          </span>
        </div>

        <div className={styles.headerActions}>
          <Button
            variant="primary"
            onClick={handleLaunch}
            disabled={launching || launched}
            style={{ background: launched ? '#3b82f6' : '#10b981', color: '#000000', fontWeight: 700 }}
          >
            {launching ? 'LAUNCHING...' : launched ? '✓ CAMPAIGN LIVE (AUTO-PILOT)' : '🚀 LAUNCH & SCHEDULE CAMPAIGN'}
          </Button>
        </div>
      </header>

      {/* Tabs */}
      <div className={styles.tabBar}>
        <button
          className={`${styles.tab} ${activeTab === 'calendar' ? styles.activeTab : ''}`}
          onClick={() => setActiveTab('calendar')}
        >
          📅 Feed Content Calendar ({posts.length} Posts)
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'video' ? styles.activeTab : ''}`}
          onClick={() => setActiveTab('video')}
        >
          🎥 Video Assets
        </button>
      </div>

      {/* Main Content Area */}
      <main className={styles.mainContent}>
        {error && <div style={{ color: '#ef4444', marginBottom: '1rem' }}>{error}</div>}

        {activeTab === 'calendar' ? (
          <div className={styles.grid}>
            {posts.length > 0 ? (
              posts.map((p: LinkedInPostItem, idx: number) => (
                <div key={p.id || idx} className={styles.card}>
                  <div className={styles.cardHeader}>
                    <span className={styles.slotTime}>
                      Day {idx + 1} • {new Date(p.scheduled_at || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: '#9ca3af', textTransform: 'uppercase' }}>
                      {p.status}
                    </span>
                  </div>

                  <div className={styles.postHook}>{p.hook}</div>
                  <div className={styles.postBody}>{p.body}</div>
                  {p.cta_text && <div className={styles.postCta}>👉 {p.cta_text}</div>}
                </div>
              ))
            ) : (
              <div style={{ color: '#9ca3af', padding: '2rem', textAlign: 'center', gridColumn: '1 / -1' }}>
                No calendar posts generated yet. Posts will be scheduled according to AI strategy plan.
              </div>
            )}
          </div>
        ) : activeTab === 'video' ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2rem', padding: '2rem 0' }}>
            {!videoUrl && !generatingVideo && (
              <div style={{ textAlign: 'center', color: '#9ca3af' }}>
                <p style={{ marginBottom: '1.5rem', fontSize: '1.1rem' }}>No video generated yet. Let our AI Director build a highly interactive video for you.</p>
                <Button variant="primary" onClick={handleGenerateVideo} style={{ background: '#55E6C1', color: '#000', fontWeight: 'bold' }}>
                  🎬 GENERATE VIDEO
                </Button>
              </div>
            )}

            {generatingVideo && (
              <div style={{ textAlign: 'center', color: '#55E6C1', padding: '3rem' }}>
                <div style={{ fontSize: '1.5rem', marginBottom: '1rem', animation: 'pulse 2s infinite' }}>🤖 AI Director is building your video...</div>
                <p style={{ color: '#9ca3af' }}>Writing script, rendering visuals, and compositing audio...</p>
              </div>
            )}

            {videoUrl && (
              <div style={{ width: '100%', maxWidth: '400px', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <div style={{ borderRadius: '12px', overflow: 'hidden', boxShadow: '0 10px 25px rgba(0,0,0,0.5)', border: '1px solid #374151' }}>
                  <video src={videoUrl} controls style={{ width: '100%', display: 'block', backgroundColor: '#000' }} />
                </div>
                
                <Button 
                  variant="primary" 
                  onClick={handleAutopilotLinkedIn}
                  disabled={autopilotLive}
                  style={{ background: autopilotLive ? '#3b82f6' : '#0a66c2', color: '#fff', fontWeight: 'bold' }}
                >
                  {autopilotLive ? '✓ LIVE ON LINKEDIN AUTOPILOT' : '🚀 AUTOPILOT TO LINKEDIN'}
                </Button>
              </div>
            )}
          </div>
        ) : null}
      </main>

      {/* Footer Safety Info */}
      <footer className={styles.footerBar}>
        <div className={styles.safetySettings}>
          <div className={styles.safetyItem}>
            🛡️ Daily Invites: <strong>{config?.daily_invite_limit || 20}/day</strong>
          </div>
          <div className={styles.safetyItem}>
            💬 Daily DMs: <strong>{config?.daily_message_limit || 30}/day</strong>
          </div>
          <div className={styles.safetyItem}>
            ⏱️ Jitter Delays: <strong>90s - 210s</strong>
          </div>
          <div className={styles.safetyItem}>
            🛑 Stop on Reply: <strong>{config?.stop_on_reply !== false ? 'ENABLED' : 'DISABLED'}</strong>
          </div>
        </div>

        <Button
          variant="primary"
          onClick={handleLaunch}
          disabled={launching || launched}
          style={{ background: launched ? '#3b82f6' : '#10b981', color: '#000000', fontWeight: 700 }}
        >
          {launched ? '✓ LIVE ON UNPILE' : 'ACTIVATE AUTO-PILOT'}
        </Button>
      </footer>
    </div>
  );
}

export default function LaunchpadPage() {
  return (
    <Suspense fallback={<div>Loading Launchpad...</div>}>
      <LaunchpadContent />
    </Suspense>
  );
}

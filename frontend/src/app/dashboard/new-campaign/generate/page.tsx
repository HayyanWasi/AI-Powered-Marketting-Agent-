'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import styles from './page.module.css';
import { aiApi, companyApi, campaignApi, ApiError } from '@/lib/api';

type GenerationState = 'idle' | 'loading' | 'success' | 'error';

function GenerateStrategyContent() {
  const searchParams = useSearchParams();
  const campaignId = searchParams.get('campaign_id');

  const [state, setState] = useState<GenerationState>('idle');
  const [artifacts, setArtifacts] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState('');
  const [engineInfo, setEngineInfo] = useState<string>('');

  useEffect(() => {
    const loadInfo = async () => {
      try {
        const info = await aiApi.info();
        setEngineInfo(String(info.version || '1.0.0'));
      } catch {
        // non-critical
      }
    };
    loadInfo();
  }, []);

  const handleStartCrafting = async () => {
    setState('loading');
    setError('');
    setArtifacts(null);

    try {
      // Step 1: Get company profile for brand context
      let companyProfile: Record<string, unknown> = {};
      let brandGuidelines: Record<string, unknown> = {};
      try {
        const profiles = await companyApi.list();
        if (profiles && profiles.length > 0) {
          const p = profiles[0];
          companyProfile = {
            company_name: p.company_name,
            brand_guidelines: p.brand_guidelines,
            brand_tone: p.brand_tone,
          };
          brandGuidelines = {
            tone: p.brand_tone || 'professional',
            guidelines: p.brand_guidelines,
          };
        }
      } catch {
        // proceed without profile
      }

      // Step 2: Get campaign details if we have an ID
      let campaignContext: Record<string, unknown> = {};
      let audience: Record<string, unknown> = {};
      let platforms: string[] = ['linkedin', 'instagram', 'twitter'];
      if (campaignId) {
        try {
          const campaign = await campaignApi.get(campaignId);
          campaignContext = {
            campaign_id: campaign.id,
            campaign_name: campaign.name,
            ...((campaign.goals as Record<string, unknown>) || {}),
          };
          audience = (campaign.target_audience as Record<string, unknown>) || {};
          platforms = campaign.platforms || platforms;
        } catch {
          // proceed without campaign
        }
      }

      // Step 3: Call AI generation
      const result = await aiApi.generate({
        campaign_context: campaignContext,
        company_profile: companyProfile,
        audience,
        platforms,
        brand_guidelines: brandGuidelines,
        reference_materials: [],
        user_intent: {},
      });

      setArtifacts(result.artifacts || result as Record<string, unknown>);
      setState('success');
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Generation failed. Please try again.';
      setError(msg);
      setState('error');
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.breadcrumbs}>
        AI Generation Workspace {engineInfo && <span style={{ color: 'var(--text-secondary)', fontFamily: 'monospace' }}>v{engineInfo}</span>}
      </div>

      <div className={styles.tabsContainer}>
        <div className={styles.tab}>
          <span className={styles.tabNumber}>01</span> Parameters
        </div>
        <div className={`${styles.tab} ${styles.tabActive}`}>
          <span className={styles.tabNumber}>02</span> Strategy Generation
        </div>
        <div className={styles.tab}>
          <span className={styles.tabNumber}>03</span> Deployment
        </div>
      </div>

      {state === 'success' && artifacts ? (
        /* ── Success: Show generated artifacts ── */
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{
            background: 'var(--bg-card)',
            border: '1px solid #10b981',
            borderRadius: '6px',
            padding: '1rem 1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            <span style={{ color: '#10b981', fontWeight: 600, fontSize: '0.875rem' }}>Campaign strategy generated successfully!</span>
          </div>

          {/* Visual Asset Preview */}
          {artifacts.image && (artifacts.image as any).image_url && artifacts.copy && (
            <div style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              padding: '1.5rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1.25rem',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <h3 style={{ fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-secondary)', margin: 0 }}>
                  Generated Campaign Post
                </h3>
                <span style={{ fontSize: '0.75rem', padding: '0.25rem 0.75rem', background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', borderRadius: '1rem', fontWeight: 600 }}>
                  {((artifacts.image as any).platform || 'Web').toUpperCase()}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <div style={{ flex: '1 1 300px', maxWidth: '400px' }}>
                  <img 
                    src={(artifacts.image as any).image_url} 
                    alt="Generated Campaign" 
                    style={{ width: '100%', height: 'auto', borderRadius: '8px', border: '1px solid var(--border-color)', objectFit: 'cover', display: 'block' }} 
                  />
                </div>
                <div style={{ flex: '2 1 300px', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                  {/* Captions */}
                  <div>
                    <h4 style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>Caption</h4>
                    <p style={{ fontSize: '1rem', lineHeight: 1.6, color: 'var(--text-primary)', margin: 0 }}>
                      {((artifacts.copy as any).captions && (artifacts.copy as any).captions.length > 0) ? (artifacts.copy as any).captions[0] : 'No caption generated.'}
                    </p>
                  </div>
                  {/* Hashtags */}
                  {((artifacts.copy as any).hashtags && (artifacts.copy as any).hashtags.length > 0) && (
                    <div>
                      <h4 style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>Hashtags</h4>
                      <p style={{ fontSize: '0.85rem', color: '#10b981', display: 'flex', gap: '0.5rem', flexWrap: 'wrap', margin: 0 }}>
                        {(artifacts.copy as any).hashtags.map((tag: string, i: number) => <span key={i}>{tag}</span>)}
                      </p>
                    </div>
                  )}
                  {/* CTAs */}
                  {((artifacts.copy as any).ctas && (artifacts.copy as any).ctas.length > 0) && (
                    <div>
                      <h4 style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.75rem', textTransform: 'uppercase' }}>Call to Action</h4>
                      <button style={{
                        background: 'transparent',
                        border: '1px solid #10b981',
                        color: '#10b981',
                        padding: '0.5rem 1.25rem',
                        borderRadius: '4px',
                        fontSize: '0.85rem',
                        cursor: 'pointer',
                        fontWeight: 600
                      }}>
                        {(artifacts.copy as any).ctas[0]}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

        </div>
      ) : (
        /* ── Idle / Loading / Error ── */
        <div className={styles.mainBox}>
          {state === 'loading' ? (
            <>
              <div className={styles.iconBox} style={{ animation: 'spin 2s linear infinite' }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
              </div>
              <h2 className={styles.title}>Synthesizing Your Campaign...</h2>
              <p className={styles.desc}>
                Aether Engine is analyzing your brief, researching your audience,<br/>
                and generating a complete data-driven strategy. This may take a moment.
              </p>
            </>
          ) : state === 'error' ? (
            <>
              <div className={styles.iconBox} style={{ background: 'rgba(239,68,68,0.1)' }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              </div>
              <h2 className={styles.title}>Generation Failed</h2>
              <p className={styles.desc} style={{ color: '#ef4444' }}>{error}</p>
              <button className={styles.craftBtn} onClick={handleStartCrafting}>
                Retry
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              </button>
            </>
          ) : (
            <>
              <div className={styles.iconBox}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z"/></svg>
              </div>
              <h2 className={styles.title}>Ready to Architect Your Strategy?</h2>
              <p className={styles.desc}>
                Aether Engine is calibrated and ready to synthesize your campaign<br/>
                goals into high-converting social assets and a data-driven<br/>
                schedule.
                {campaignId && (
                  <><br/><span style={{ fontSize: '0.7rem', fontFamily: 'monospace', color: 'var(--text-secondary)', marginTop: '0.5rem', display: 'block' }}>Campaign ID: {campaignId}</span></>
                )}
              </p>
              <button className={styles.craftBtn} onClick={handleStartCrafting}>
                Start Crafting
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function GenerateStrategy() {
  return (
    <Suspense fallback={
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
        Loading workspace...
      </div>
    }>
      <GenerateStrategyContent />
    </Suspense>
  );
}

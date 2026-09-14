'use client';

import { Suspense, useCallback, useEffect, useRef, useState } from 'react';
import styles from './page.module.css';
import Link from 'next/link';
import Button from '@/components/ui/Button';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  ApiError,
  CampaignPlanDocument,
  PlanMessage,
  campaignApi,
  linkedinApi,
  planApi,
} from '@/lib/api';
import gsap from 'gsap';

// ─── Section state interface ──────────────────────────────────────────────────
interface SectionState {
  core_strategy: boolean;
  channel_plan: boolean;
  measurement: boolean;
  competitive: boolean;
}

// ── Platform Helper Function for Visual Badges ──
function renderPlatformBadge(platformName: string, cadence?: string) {
  const p = platformName.toLowerCase();

  if (p.includes('linkedin')) {
    return (
      <div className={`${styles.platformBadge} ${styles.platformLinkedin}`}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z" /></svg>
        <span>LinkedIn</span>
        {cadence && <span className={styles.cadenceTag}>{cadence}</span>}
      </div>
    );
  }

  if (p.includes('instagram')) {
    return (
      <div className={`${styles.platformBadge} ${styles.platformInstagram}`}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="2" width="20" height="20" rx="5" ry="5" /><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" /><line x1="17.5" y1="6.5" x2="17.51" y2="6.5" /></svg>
        <span>Instagram</span>
        {cadence && <span className={styles.cadenceTag}>{cadence}</span>}
      </div>
    );
  }

  if (p.includes('youtube')) {
    return (
      <div className={`${styles.platformBadge} ${styles.platformYoutube}`}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" /></svg>
        <span>YouTube</span>
        {cadence && <span className={styles.cadenceTag}>{cadence}</span>}
      </div>
    );
  }

  return (
    <div className={`${styles.platformBadge} ${styles.platformGeneric}`}>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" /></svg>
      <span>{platformName}</span>
      {cadence && <span className={styles.cadenceTag}>{cadence}</span>}
    </div>
  );
}

// ─── Plan Page Content ────────────────────────────────────────────────────────
function PlanPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const campaignId = searchParams.get('campaign_id') || '';

  // Step state: 2 = Research Plan Cards preview, 3 = Split Review with Chat
  const [step, setStep] = useState<number>(2);

  const [plan, setPlan] = useState<CampaignPlanDocument | null>(null);
  const [messages, setMessages] = useState<PlanMessage[]>([]);
  const [drafting, setDrafting] = useState(false);
  const [approving, setApproving] = useState(false);
  const [loadingPlan, setLoadingPlan] = useState(true);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  // Expandable Gemini Plan Cards state (Step 2)
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({
    audience: false,
    strategy: false,
    channel: false,
    measurement: false,
  });

  // Expandable Accordion state (Step 3)
  const [openSections, setOpenSections] = useState<SectionState>({
    core_strategy: true,
    channel_plan: false,
    measurement: false,
    competitive: false,
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatThreadRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // ── GSAP Message Bubble Entrance Animation ──
  useEffect(() => {
    if (!chatThreadRef.current) return;
    const bubbles = chatThreadRef.current.querySelectorAll(`.${styles.chatMsg}`);
    const lastBubble = bubbles[bubbles.length - 1];
    if (lastBubble) {
      gsap.fromTo(
        lastBubble,
        { opacity: 0, y: 14 },
        { opacity: 1, y: 0, duration: 0.35, ease: 'power2.out' }
      );
    }
  }, [messages]);

  // ── Load existing plan + messages on mount ──
  useEffect(() => {
    if (!campaignId) {
      setLoadingPlan(false);
      return;
    }
    (async () => {
      try {
        const [planDoc, msgs] = await Promise.all([
          planApi.get(campaignId).catch(() => null),
          planApi.getMessages(campaignId).catch(() => []),
        ]);
        if (planDoc) {
          setPlan(planDoc);
          setStep(3); // If plan exists, show Step 3 split review
        }
        setMessages(Array.isArray(msgs) ? msgs : []);
      } catch {
        // Plan doesn't exist yet — stay on Step 2 preview
      } finally {
        setLoadingPlan(false);
      }
    })();
  }, [campaignId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // ── Trigger draft via AI Panel ──
  const handleDraft = useCallback(async () => {
    if (!campaignId || drafting) return null;
    setDrafting(true);
    setError('');
    try {
      const campaign = await campaignApi.get(campaignId).catch(() => null);
      const goals = (campaign?.goals as Record<string, unknown>) || {};

      const drafted = await planApi.draft(campaignId, {
        user_goal: String(goals.primary || campaign?.name || ''),
        event_name: campaign?.name || '',
        platforms: campaign?.platforms || ['linkedin', 'instagram'],
        language: 'en',
      });
      setPlan(drafted);
      setMessages([]);
      setStep(3); // Move to Step 3 review
      return drafted;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Draft failed. Please try again.');
      return null;
    } finally {
      setDrafting(false);
    }
  }, [campaignId, drafting]);

  // ── Refine Plan Chat Message ──
  const handleSend = async (customText?: string) => {
    const text = (customText || input).trim();
    if (!text || sending || !campaignId) return;
    setInput('');
    setSending(true);
    setError('');

    let currentPlan = plan;

    // If no plan in local state, try loading from DB before drafting a new one
    if (!currentPlan) {
      try {
        const existingPlan = await planApi.get(campaignId);
        if (existingPlan) {
          currentPlan = existingPlan;
          setPlan(existingPlan);
        }
      } catch {
        // No plan in DB either — draft a new one
        currentPlan = await handleDraft();
        if (!currentPlan) {
          setSending(false);
          return;
        }
      }
    }

    setStep(3); // Ensure Step 3 (Refine with AI split view) is open

    const userMsg: PlanMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      language: currentPlan?.language || 'en',
      sections_targeted: [],
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const result = await planApi.sendMessage(campaignId, text);
      setPlan(result.plan);
      const assistantMsg: PlanMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: result.reply,
        language: currentPlan?.language || 'en',
        sections_targeted: [],
        resulting_version: result.version,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Refinement failed.');
    } finally {
      setSending(false);
    }
  };


  // ── Approve Plan ──
  const handleApprove = async () => {
    if (!campaignId || approving || !plan) return;
    setApproving(true);
    setError('');
    try {
      await planApi.approve(campaignId);
      setPlan((prev) => (prev ? { ...prev, approved: true, status: 'Approved' } : prev));
      // Trigger AI content & sequence generation
      await linkedinApi.generate(campaignId).catch(() => null);
      // Navigate to Launchpad screen
      router.push(`/dashboard/new-campaign/launchpad?campaign_id=${campaignId}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Approval failed.');
    } finally {
      setApproving(false);
    }
  };

  const toggleCard = (key: string) => {
    setExpandedCards((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const toggleSection = (key: keyof SectionState) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const isApproved = plan?.approved === true || plan?.status === 'Approved';

  // ── RENDER ──
  return (
    <div className={styles.container}>

      {/* ── Top Header Navigation Bar ── */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <div className={styles.breadcrumbBar}>
            <span>CAMPAIGNS</span> &gt; <span>NEW CAMPAIGN</span> &gt;{' '}
            <span className={styles.breadcrumbActive}>
              {step === 2 ? 'STEP 2: RESEARCH PLAN' : 'STEP 3: REFINEMENT CANVAS'}
            </span>
          </div>
          <div className={styles.titleRow}>
            <h1 className={styles.title}>Campaign Strategy &amp; Research Workspace</h1>
            <span className={styles.campaignIdBadge}>
              {campaignId ? `ID: ${campaignId.slice(0, 12)}...` : 'ID: CT-4920-X'}
            </span>
          </div>
        </div>

        <div className={styles.headerRight}>
          <div
            className={`${styles.statusBadge} ${isApproved
                ? styles.statusApproved
                : plan
                  ? styles.statusRefining
                  : styles.statusDrafting
              }`}
          >
            <span className={styles.dot} />
            {drafting ? 'DRAFTING WORKSPACE...' : isApproved ? 'PLAN APPROVED' : plan ? 'REFINING DRAFT' : 'STEP 2 PENDING'}
          </div>

          {!isApproved && plan && (
            <Button variant="primary" onClick={handleApprove} disabled={approving} className={styles.headerCtaBtn}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12" /></svg>
              {approving ? 'APPROVING...' : 'APPROVE PLAN'}
            </Button>
          )}

          {isApproved && (
            <Link href={`/dashboard/new-campaign/launchpad?campaign_id=${campaignId}`}>
              <Button variant="primary" className={styles.headerCtaBtn}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" /></svg>
                VIEW CONTENT ASSETS
              </Button>
            </Link>
          )}
        </div>
      </header>

      {/* ── Main Workspace Body ── */}
      <div className={styles.body}>
        {loadingPlan ? (
          <div className={styles.loadingWrap}>
            <div className={styles.spinner} />
            <span>Synchronizing Neural Research Workspace...</span>
          </div>
        ) : step === 2 && !plan ? (
          /* ━━━━━━━━━━━━━━━━━━━━ STEP 2: AI RESEARCH PLAN ━━━━━━━━━━━━━━━━━━━━ */
          <div className={styles.planPaneSingle}>
            <div className={styles.stepperHeader}>
              <div className={styles.stepperBadge}>
                <span className={styles.pulseDot} />
                STEP 2 OF 3
              </div>
              <div className={styles.stepperBars}>
                <div className={styles.stepperBarActive} />
                <div className={styles.stepperBarActive} />
                <div className={styles.stepperBar} />
              </div>
            </div>

            <div className={styles.step2Card}>
              <div className={styles.step2CardHeader}>
                <div className={styles.aetherIconWrap}>
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polygon points="12 2 2 7 12 12 22 7 12 2" />
                    <polyline points="2 12 12 17 22 12" />
                    <polyline points="2 17 12 22 22 17" />
                  </svg>
                </div>
                <div>
                  <h2 className={styles.step2Title}>Campaign Research &amp; Execution Plan</h2>
                  <p className={styles.step2Subtitle}>
                    Aether Neural Engine has synthesized market parameters and audience intelligence for your campaign.
                  </p>
                </div>
              </div>

              {/* 4 Research Plan Cards */}
              <div className={styles.planCardsGrid}>

                {/* Card 1: Audience & Market Research */}
                <div
                  className={`${styles.planCard} ${expandedCards.audience ? styles.planCardExpanded : ''}`}
                  onClick={() => toggleCard('audience')}
                >
                  <div className={styles.planIcon}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>
                  </div>
                  <div className={styles.planContent}>
                    <div className={styles.planCardTitle}>Audience &amp; Market Research</div>
                    <div className={styles.planDesc}>
                      Analyze target demographics, pain points, psychographics, and current market trends.
                    </div>
                    {expandedCards.audience && (
                      <div className={styles.planDetail}>
                        • Deep-dive into buyer pain points &amp; purchasing motivations<br />
                        • Competitor landscape mapping &amp; white space identification<br />
                        • Social listening data &amp; intent signal synthesis<br />
                        • Persona behavioral calibration
                      </div>
                    )}
                  </div>
                  <svg className={`${styles.planChevron} ${expandedCards.audience ? styles.planChevronExpanded : ''}`} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9" /></svg>
                </div>

                {/* Card 2: Core Strategy & Messaging */}
                <div
                  className={`${styles.planCard} ${expandedCards.strategy ? styles.planCardExpanded : ''}`}
                  onClick={() => toggleCard('strategy')}
                >
                  <div className={styles.planIcon}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" /></svg>
                  </div>
                  <div className={styles.planContent}>
                    <div className={styles.planCardTitle}>Core Strategy &amp; Messaging</div>
                    <div className={styles.planDesc}>
                      Formulate value proposition, positioning statement, and primary messaging pillars.
                    </div>
                    {expandedCards.strategy && (
                      <div className={styles.planDetail}>
                        • Campaign central theme &amp; big idea generation<br />
                        • Key message hierarchy development<br />
                        • Tone of voice &amp; brand alignment calibration<br />
                        • Visual &amp; copy concept direction
                      </div>
                    )}
                  </div>
                  <svg className={`${styles.planChevron} ${expandedCards.strategy ? styles.planChevronExpanded : ''}`} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9" /></svg>
                </div>

                {/* Card 3: Channel Plan & Content Calendar */}
                <div
                  className={`${styles.planCard} ${expandedCards.channel ? styles.planCardExpanded : ''}`}
                  onClick={() => toggleCard('channel')}
                >
                  <div className={styles.planIcon}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></svg>
                  </div>
                  <div className={styles.planContent}>
                    <div className={styles.planCardTitle}>Channel Plan &amp; Content Calendar</div>
                    <div className={styles.planDesc}>
                      Map distribution channels (LinkedIn, Instagram, YouTube) and posting cadence.
                    </div>
                    {expandedCards.channel && (
                      <div className={styles.planDetail}>
                        • Target platform selection &amp; posting frequency<br />
                        • Content format matrix (Carousels, Video Scripts, Posts)<br />
                        • 30-day cross-channel narrative flow<br />
                        • Automated scheduling triggers
                      </div>
                    )}
                  </div>
                  <svg className={`${styles.planChevron} ${expandedCards.channel ? styles.planChevronExpanded : ''}`} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9" /></svg>
                </div>

                {/* Card 4: Measurement & KPIs */}
                <div
                  className={`${styles.planCard} ${expandedCards.measurement ? styles.planCardExpanded : ''}`}
                  onClick={() => toggleCard('measurement')}
                >
                  <div className={styles.planIcon}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="20" x2="12" y2="10" /><line x1="18" y1="20" x2="18" y2="4" /><line x1="6" y1="20" x2="6" y2="14" /></svg>
                  </div>
                  <div className={styles.planContent}>
                    <div className={styles.planCardTitle}>Measurement &amp; KPIs</div>
                    <div className={styles.planDesc}>
                      Establish conversion benchmarks, tracking mechanisms, and success metrics.
                    </div>
                    {expandedCards.measurement && (
                      <div className={styles.planDetail}>
                        • Primary KPI targets &amp; performance metrics<br />
                        • Attribution model setup<br />
                        • Live performance tracking dashboard<br />
                        • Optimization playbooks
                      </div>
                    )}
                  </div>
                  <svg className={`${styles.planChevron} ${expandedCards.measurement ? styles.planChevronExpanded : ''}`} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9" /></svg>
                </div>

              </div>

              {/* Step 2 Prompt Box */}
              <div className={styles.chatInputWrapStep2}>
                <textarea
                  className={styles.chatInput}
                  placeholder="Tell Aether AI to adjust research parameters... e.g. 'Focus heavily on LinkedIn B2B' or 'Increase video content ratio'"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                />
                <Button
                  variant="primary"
                  onClick={() => handleSend()}
                  disabled={sending || drafting || !input.trim()}
                  className={styles.chatSendBtn}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
                </Button>
              </div>

              {error && <div className={styles.errorBanner}>{error}</div>}

              {/* Step 2 Toolbar Actions */}
              <div className={styles.step2FooterToolbar}>
                <Link href="/dashboard/new-campaign">
                  <Button variant="ghost">&larr; BACK TO BRIEF</Button>
                </Link>
                <Button
                  variant="primary"
                  onClick={() => handleDraft()}
                  disabled={drafting || !campaignId}
                  className={styles.approveStartBtn}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z" /></svg>
                  {drafting ? 'DRAFTING PLAN WITH AI PANEL...' : 'APPROVE & START RESEARCH'}
                </Button>
              </div>
            </div>
          </div>
        ) : (
          /* ━━━━━━━━━━━━━━━━━━━━ STEP 3: CAMPAIGN PLAN REVIEW & REFINEMENT (Split View) ━━━━━━━━━━━━━━━━━━━━ */
          <>
            {/* Left: Accordion Canvas Content */}
            <div className={styles.planPane}>

              <div className={styles.versionCard}>
                <div className={styles.versionBadge}>v{plan?.version || 1}</div>
                <div>
                  <h3 className={styles.versionTitle}>{plan?.title || 'Campaign Strategy & Content Blueprint'}</h3>
                  <p className={styles.versionSub}>Generated by Aether Engine 5-Specialist Neural Panel</p>
                </div>
              </div>

              {error && <div className={styles.errorBanner}>{error}</div>}

              {/* Accordions */}
              <div className={styles.accordionContainer}>

                {/* Accordion 1: Core Strategy */}
                <div className={styles.accordion}>
                  <button
                    className={styles.accordionHeader}
                    onClick={() => toggleSection('core_strategy')}
                  >
                    <div className={styles.accordionHeaderLeft}>
                      <div className={styles.accordionIconWrap}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" /></svg>
                      </div>
                      <span>CORE STRATEGY &amp; MESSAGING</span>
                    </div>
                    <svg
                      className={`${styles.accordionIcon} ${openSections.core_strategy ? styles.accordionIconOpen : ''}`}
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <polyline points="18 15 12 9 6 15" />
                    </svg>
                  </button>
                  {openSections.core_strategy && (
                    <div className={styles.accordionBody}>
                      {plan?.core_strategy?.objective && (
                        <div className={styles.fieldGroup}>
                          <div className={styles.fieldLabel}>CAMPAIGN OBJECTIVE</div>
                          <div className={styles.fieldValue}>{plan.core_strategy.objective}</div>
                        </div>
                      )}
                      {plan?.core_strategy?.unique_selling_proposition && (
                        <div className={styles.fieldGroup}>
                          <div className={styles.fieldLabel}>UNIQUE SELLING PROPOSITION (USP)</div>
                          <div className={styles.fieldValueHighlight}>
                            {plan.core_strategy.unique_selling_proposition}
                          </div>
                        </div>
                      )}
                      {plan?.core_strategy?.positioning_statement && (
                        <div className={styles.fieldGroup}>
                          <div className={styles.fieldLabel}>POSITIONING STATEMENT</div>
                          <div className={styles.fieldValue}>{plan.core_strategy.positioning_statement}</div>
                        </div>
                      )}
                      {plan?.core_strategy?.messaging_pillars && plan.core_strategy.messaging_pillars.length > 0 && (
                        <div className={styles.fieldGroup}>
                          <div className={styles.fieldLabel}>MESSAGING PILLARS</div>
                          <div className={styles.pillContainer}>
                            {plan.core_strategy.messaging_pillars.map((p, i) => (
                              <span key={i} className={styles.pill}>
                                {p}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {plan?.core_strategy?.tone_of_voice && (
                        <div className={styles.fieldGroup}>
                          <div className={styles.fieldLabel}>TONE OF VOICE</div>
                          <div className={styles.fieldValue}>{plan.core_strategy.tone_of_voice}</div>
                        </div>
                      )}
                      {plan?.core_strategy?.personas && plan.core_strategy.personas.length > 0 && (
                        <div className={styles.fieldGroup}>
                          <div className={styles.fieldLabel}>TARGET AUDIENCE PERSONAS</div>
                          {plan.core_strategy.personas.map((p, i) => (
                            <div key={i} className={styles.personaCard}>
                              <div className={styles.personaName}>{p.name}</div>
                              <div className={styles.personaDesc}>{p.description}</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Accordion 2: Channel Plan & Content Calendar */}
                <div className={styles.accordion}>
                  <button
                    className={styles.accordionHeader}
                    onClick={() => toggleSection('channel_plan')}
                  >
                    <div className={styles.accordionHeaderLeft}>
                      <div className={styles.accordionIconWrap}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></svg>
                      </div>
                      <span>CHANNEL PLAN &amp; CONTENT CALENDAR</span>
                    </div>
                    <svg
                      className={`${styles.accordionIcon} ${openSections.channel_plan ? styles.accordionIconOpen : ''}`}
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <polyline points="18 15 12 9 6 15" />
                    </svg>
                  </button>
                  {openSections.channel_plan && (
                    <div className={styles.accordionBody}>
                      {plan?.channel_plan?.overall_cadence && (
                        <div className={styles.fieldGroup}>
                          <div className={styles.fieldLabel}>OVERALL PUBLISHING CADENCE</div>
                          <div className={styles.fieldValue}>{plan.channel_plan.overall_cadence}</div>
                        </div>
                      )}

                      {/* Visual Platform Badges Component */}
                      <div className={styles.fieldGroup}>
                        <div className={styles.fieldLabel}>TARGET PLATFORMS &amp; CADENCE</div>
                        <div className={styles.platformBadgeGrid}>
                          {plan?.channel_plan?.platforms && plan.channel_plan.platforms.length > 0 ? (
                            plan.channel_plan.platforms.map((p, i) => (
                              <div key={i}>
                                {renderPlatformBadge(p.platform, p.posting_cadence)}
                              </div>
                            ))
                          ) : (
                            <>
                              {renderPlatformBadge('LinkedIn', '3x / week')}
                              {renderPlatformBadge('Instagram', '5x / week')}
                              {renderPlatformBadge('YouTube', '1x / week')}
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Accordion 3: Measurement & KPIs */}
                <div className={styles.accordion}>
                  <button
                    className={styles.accordionHeader}
                    onClick={() => toggleSection('measurement')}
                  >
                    <div className={styles.accordionHeaderLeft}>
                      <div className={styles.accordionIconWrap}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="20" x2="12" y2="10" /><line x1="18" y1="20" x2="18" y2="4" /><line x1="6" y1="20" x2="6" y2="14" /></svg>
                      </div>
                      <span>MEASUREMENT &amp; KPIS</span>
                    </div>
                    <svg
                      className={`${styles.accordionIcon} ${openSections.measurement ? styles.accordionIconOpen : ''}`}
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <polyline points="18 15 12 9 6 15" />
                    </svg>
                  </button>
                  {openSections.measurement && (
                    <div className={styles.accordionBody}>
                      {plan?.measurement?.definition_of_success && (
                        <div className={styles.fieldGroup}>
                          <div className={styles.fieldLabel}>DEFINITION OF SUCCESS</div>
                          <div className={styles.fieldValue}>{plan.measurement.definition_of_success}</div>
                        </div>
                      )}
                      {plan?.measurement?.kpis && plan.measurement.kpis.length > 0 && (
                        <div className={styles.fieldGroup}>
                          <div className={styles.fieldLabel}>KEY PERFORMANCE INDICATORS</div>
                          <div className={styles.kpiGrid}>
                            {plan.measurement.kpis.map((k, i) => (
                              <div key={i} className={styles.kpiCard}>
                                <span className={styles.kpiName}>{k.name}</span>
                                <span className={styles.kpiTarget}>{k.target}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Accordion 4: Competitive Intelligence */}
                <div className={styles.accordion}>
                  <button
                    className={styles.accordionHeader}
                    onClick={() => toggleSection('competitive')}
                  >
                    <div className={styles.accordionHeaderLeft}>
                      <div className={styles.accordionIconWrap}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" /></svg>
                      </div>
                      <span>COMPETITIVE INTELLIGENCE</span>
                    </div>
                    <svg
                      className={`${styles.accordionIcon} ${openSections.competitive ? styles.accordionIconOpen : ''}`}
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <polyline points="18 15 12 9 6 15" />
                    </svg>
                  </button>
                  {openSections.competitive && (
                    <div className={styles.accordionBody}>
                      {plan?.competitive?.differentiation_angle && (
                        <div className={styles.fieldGroup}>
                          <div className={styles.fieldLabel}>DIFFERENTIATION ANGLE</div>
                          <div className={styles.fieldValue}>{plan.competitive.differentiation_angle}</div>
                        </div>
                      )}
                    </div>
                  )}
                </div>

              </div>
            </div>

            {/* Right: AI Refinement Chat Drawer / Sidebar (420px) */}
            <div className={styles.chatPanel}>
              <div className={styles.chatHeader}>
                <div className={styles.chatHeaderIconWrap}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z" /></svg>
                </div>
                <div>
                  <h3 className={styles.chatHeaderTitle}>REFINE WITH AI ASSISTANT</h3>
                  <span className={styles.chatHeaderStatus}>ACTIVE REFINEMENT SESSION</span>
                </div>
              </div>

              {/* Chat Thread */}
              <div className={styles.chatMessages} ref={chatThreadRef}>
                {/* Initial AI Welcome Bubble */}
                <div className={`${styles.chatMsg} ${styles.chatMsgAi}`}>
                  <div className={`${styles.chatAvatar} ${styles.chatAvatarAi}`}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z" /></svg>
                  </div>
                  <div className={`${styles.chatBubble} ${styles.chatBubbleAi}`}>
                    I have synthesized your campaign strategy blueprint based on your parameters. Review the sections on the left canvas. You can instruct me to refine any pillar, adjust platform cadences, or recalibrate tone of voice.
                  </div>
                </div>

                {messages.map((m) => (
                  <div
                    key={m.id}
                    className={`${styles.chatMsg} ${m.role === 'user' ? styles.chatMsgUser : styles.chatMsgAi
                      }`}
                  >
                    <div
                      className={`${styles.chatAvatar} ${m.role === 'user' ? styles.chatAvatarUser : styles.chatAvatarAi
                        }`}
                    >
                      {m.role === 'user' ? 'U' : (
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z" /></svg>
                      )}
                    </div>
                    <div
                      className={`${styles.chatBubble} ${m.role === 'user' ? styles.chatBubbleUser : styles.chatBubbleAi
                        }`}
                    >
                      {m.content}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>

              {/* Chat Input Bar */}
              <div className={styles.chatInputArea}>
                <div className={styles.chatInputWrap}>
                  <textarea
                    className={styles.chatInput}
                    placeholder="Ask AI to refine strategy or content..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSend();
                      }
                    }}
                  />
                  <Button
                    variant="primary"
                    onClick={() => handleSend()}
                    disabled={sending || !input.trim()}
                    className={styles.chatSendBtn}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
                  </Button>
                </div>
                <div className={styles.chatHint}>
                  Press Enter to send • Shift+Enter for new line
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Default Page Export wrapped in Suspense ──────────────────────────────────
export default function PlanPage() {
  return (
    <Suspense
      fallback={
        <div className={styles.loadingWrap}>
          <div className={styles.spinner} />
          <span>Loading Plan Workspace…</span>
        </div>
      }
    >
      <PlanPageContent />
    </Suspense>
  );
}

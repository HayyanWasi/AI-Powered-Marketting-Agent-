'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import styles from './page.module.css';
import Button from '@/components/ui/Button';
import {
  IntakeChecklistState,
  campaignApi,
  intakeApi,
} from '@/lib/api';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  language?: string;
}

export default function NewCampaign() {
  const router = useRouter();

  // Campaign ID (generated on client mount or loaded from session)
  const [campaignId, setCampaignId] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);

  // Checklist & Readiness State
  const [checklist, setChecklist] = useState<IntakeChecklistState>({});
  const [isComplete, setIsComplete] = useState(false);
  const [guestConfirmNeeded, setGuestConfirmNeeded] = useState(false);
  const [guestDetected, setGuestDetected] = useState<{ name: string; title: string } | null>(null);
  const [creating, setCreating] = useState(false);

  const messageEndRef = useRef<HTMLDivElement>(null);

  // 1. Initialize or load persistent conversation
  useEffect(() => {
    let cid = localStorage.getItem('active_intake_campaign_id');
    if (!cid) {
      cid = crypto.randomUUID();
      localStorage.setItem('active_intake_campaign_id', cid);
    }
    setCampaignId(cid);

    const loadHistory = async () => {
      try {
        const data = await intakeApi.getHistory(cid);
        if (data.history && data.history.length > 0) {
          setMessages(
            data.history.map((h) => ({
              id: h.id,
              role: h.role,
              content: h.content,
              language: h.language,
            }))
          );
        } else {
          // Welcome greeting
          setMessages([
            {
              id: 'welcome',
              role: 'assistant',
              content:
                "Assalam-o-Alaikum! Main Aether AI hoon. Aap apni kis product, event ya service ke liye marketing campaign chalana chahte hain?",
            },
          ]);
        }
        if (data.checklist) setChecklist(data.checklist);
        setIsComplete(data.is_complete || false);
      } catch (err) {
        // Fallback welcome message
        setMessages([
          {
            id: 'welcome',
            role: 'assistant',
            content:
              "Assalam-o-Alaikum! Main Aether AI hoon. Aap apni kis product, event ya service ke liye marketing campaign chalana chahte hain?",
          },
        ]);
      }
    };

    loadHistory();
  }, []);

  // Scroll to bottom on new message
  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  // 2. Send Message Handler
  const handleSend = async (customText?: string) => {
    const text = (customText || input).trim();
    if (!text || sending || !campaignId) return;

    setInput('');
    setSending(true);

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const res = await intakeApi.sendMessage(campaignId, text);
      const aiMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: res.reply,
        language: res.language,
      };
      setMessages((prev) => [...prev, aiMsg]);
      if (res.checklist) setChecklist(res.checklist);
      setIsComplete(res.is_complete || false);

      if (res.guest_confirmation_needed && res.guest_detected) {
        setGuestConfirmNeeded(true);
        setGuestDetected(res.guest_detected);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: 'Apki message receive ho gayi hai! Kripya target audience aur main goal ke baare mein thoda mazeed batayein.',
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  // 3. Confirm Guest Details
  const handleConfirmGuest = async (confirmed: boolean) => {
    if (!campaignId || !guestDetected) return;
    setGuestConfirmNeeded(false);

    try {
      const res = await intakeApi.confirmGuest(
        campaignId,
        guestDetected.name,
        guestDetected.title,
        confirmed
      );
      if (res.checklist) setChecklist(res.checklist);
      setIsComplete(res.is_complete || false);

      let content = `✅ Guest confirmed: **${guestDetected.name}**!`;
      if (confirmed) {
        if (res.checklist?.guest_profile) {
          content += `\n\n**Research Complete!**\nFound this bio: _${res.checklist.guest_profile.professional_biography}_`;
        } else {
          content += `\n\n(Guest web research attempted, but no public bio found.)`;
        }
      } else {
        content = `Skipping guest details. Campaign strategy will focus 100% on core offer value.`;
      }

      const sysMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content,
      };
      setMessages((prev) => [...prev, sysMsg]);
    } catch (err) {
      console.warn('Guest confirmation error:', err);
    }
  };

  // 4. Proceed to Step 2 Plan Drafting
  const handleDraftStrategy = async () => {
    if (!campaignId || creating) return;
    setCreating(true);

    try {
      const primaryGoal =
        checklist.event_name ||
        messages.find((m) => m.role === 'user')?.content ||
        'AI Marketing Campaign';

      const campaign = await campaignApi.create({
        name: primaryGoal.slice(0, 90).trim(),
        goals: {
          primary: primaryGoal,
          metrics: [],
          targets: {
            guest_name: checklist.guest_name || undefined,
            guest_position: checklist.guest_title || undefined,
          },
        },
        target_audience: {
          segments: checklist.target_audience ? [checklist.target_audience] : [],
          demographics: {},
          interests: [],
        },
        platforms: ['linkedin', 'instagram', 'twitter', 'facebook'],
        schedule: {
          start_date: new Date().toISOString(),
          end_date: new Date(Date.now() + 30 * 24 * 3600 * 1000).toISOString(),
          timezone: 'UTC',
        },
        metadata: {
          created_from: 'intake-chat',
          curriculum_breakdown: checklist.curriculum_breakdown || undefined,
          outcome_deliverable: checklist.outcome_deliverable || undefined,
          registration_link: checklist.registration_link || undefined,
        },
      });

      // Migrate intake checklist from session UUID → real campaign ID
      // This is critical: the intake was saved under `cid` (a browser UUID),
      // but the campaign was created with a DB-generated UUID (campaign.id).
      // Without this, content generation can't find the event/guest data.
      try {
        const migrateResult = await intakeApi.migrateSession(campaignId, campaign.id);
        console.log('[Intake] Migrated session:', migrateResult);
      } catch (migrateErr) {
        console.warn('[Intake] Session migration failed (non-fatal):', migrateErr);
      }

      // Clear current intake session for next creation
      localStorage.removeItem('active_intake_campaign_id');
      router.push(`/dashboard/new-campaign/plan?campaign_id=${campaign.id}`);
    } catch (err) {
      alert('Could not start campaign plan draft. Please try again.');
      setCreating(false);
    }
  };

  // Reset / Clear current active campaign chat
  const handleResetChat = async () => {
    if (!campaignId) return;
    try {
      await intakeApi.resetSession(campaignId);
    } catch (e) {
      console.warn('Failed to reset DB session', e);
    }
    localStorage.removeItem('active_intake_campaign_id');
    const newCid = crypto.randomUUID();
    localStorage.setItem('active_intake_campaign_id', newCid);
    setCampaignId(newCid);
    setChecklist({});
    setIsComplete(false);
    setGuestConfirmNeeded(false);
    setGuestDetected(null);
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content:
          'Assalam-o-Alaikum! Main Aether AI hoon. Aap apni kis product, event ya service ke liye marketing campaign chalana chahte hain?',
      },
    ]);
  };

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <div>
          <div className={styles.headerBadge}>
            <span className={styles.pulseDot} />
            AI CONVERSATIONAL INTAKE — STEP 1 OF 3
          </div>
          <h1 className={styles.title}>Campaign AI Assistant</h1>
        </div>

        <div className={styles.headerRight}>
          <div className={`${styles.checklistBadge} ${isComplete ? styles.complete : ''}`}>
            {isComplete ? '🟢 Context Complete (100%)' : '🟡 Gathering Details...'}
          </div>

          <Button variant="ghost" onClick={handleResetChat} title="Clear conversation & start fresh">
            🗑️ Reset Chat
          </Button>

          <Button
            variant="primary"
            onClick={handleDraftStrategy}
            disabled={!isComplete || creating}
            className={styles.draftPlanBtn}
          >
            {creating ? 'DRAFTING PLAN...' : '✨ DRAFT STRATEGY PLAN'}
          </Button>
        </div>
      </header>

      {/* Main ChatGPT Interface */}
      <div className={styles.chatContainer}>
        {/* Message Stream */}
        <div className={styles.messageStream}>
          {messages.map((m) => (
            <div key={m.id} className={`${styles.messageBubble} ${styles[m.role]}`}>
              <div className={`${styles.avatar} ${styles[m.role]}`}>
                {m.role === 'user' ? 'YOU' : 'AI'}
              </div>
              <div className={styles.bubbleContent}>
                {m.content}

                {/* Guest Confirmation Card rendered in Assistant stream */}
                {m.role === 'assistant' && guestConfirmNeeded && guestDetected && (
                  <div className={styles.guestConfirmCard}>
                    <div className={styles.guestConfirmHeader}>
                      <span>👤 GUEST DETECTED</span>
                    </div>
                    <div>
                      <strong>{guestDetected.name}</strong> {guestDetected.title && `(${guestDetected.title})`}
                    </div>
                    <div className={styles.guestConfirmActions}>
                      <button className={styles.confirmBtn} onClick={() => handleConfirmGuest(true)}>
                        Confirm Guest
                      </button>
                      <button className={styles.editBtn} onClick={() => handleConfirmGuest(false)}>
                        Skip / No Guest
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          {sending && (
            <div className={`${styles.messageBubble} ${styles.assistant}`}>
              <div className={`${styles.avatar} ${styles.assistant}`}>AI</div>
              <div className={styles.bubbleContent}>Thinking &amp; analyzing parameters...</div>
            </div>
          )}
          <div ref={messageEndRef} />
        </div>

        {/* Conversation Starters */}
        <div className={styles.startersRow}>
          <button
            className={styles.starterChip}
            onClick={() => handleSend('Mujhe 19-August ko Bahria Auditorium mein AI Automation Seminar karwana hai Zia Ullah Khan ke sath.')}
          >
            🎤 AI Seminar with Guest Speaker
          </button>
          <button
            className={styles.starterChip}
            onClick={() => handleSend('We are launching a new B2B Autonomous AI Agent SaaS tool for Tech Founders.')}
          >
            🚀 B2B SaaS Product Launch
          </button>
          <button
            className={styles.starterChip}
            onClick={() => handleSend('Create a 50% discount flash sale campaign for online coding bootcamps.')}
          >
            ⚡ E-commerce Flash Sale
          </button>
        </div>

        {/* Input Bar */}
        <div className={styles.inputBar}>
          <textarea
            className={styles.chatTextarea}
            placeholder="Type your campaign goal, guest, or details in Roman Urdu or English..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          />
          <button className={styles.sendBtn} onClick={() => handleSend()} disabled={sending || !input.trim()}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

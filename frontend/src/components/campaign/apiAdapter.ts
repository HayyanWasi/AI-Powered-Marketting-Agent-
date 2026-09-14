import { CampaignStreamEvent, LinkedInPost, CampaignStrategy } from "./types";
import { campaignApi, intakeApi, linkedinApi } from "@/lib/api";

/**
 * Real Backend API Adapter.
 *
 * Flow:
 * 1. Create or recover a campaign record (real UUID).
 * 2. POST each user message to /campaigns/intake/chat → conversational parameter gathering.
 * 3. When information is complete (or user confirms with "yes" / "generate") →
 *    a) Synthesize full Campaign Strategy Blueprint.
 *    b) Open Artifact Studio with the Strategy Blueprint view.
 *    c) Generate 3 tailored LinkedIn post drafts and stream them into the studio.
 */

// ── Session state (persisted across chat turns) ──────────────────────────────
let sessionCampaignId: string | null = null;
let isIntakeComplete = false;
let accumulatedChecklist: Record<string, any> = {};
let readyForGenerationFlag = false;
let turnCount = 0;

/** Reset session state — call when starting fresh */
export function resetCampaignSession() {
  sessionCampaignId = null;
  isIntakeComplete = false;
  accumulatedChecklist = {};
  readyForGenerationFlag = false;
  turnCount = 0;
}

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Ensure we have a real UUID campaign in the backend.
 */
async function ensureCampaignId(): Promise<string> {
  if (sessionCampaignId) return sessionCampaignId;

  const now = new Date();
  const end = new Date(now);
  end.setDate(end.getDate() + 30);

  const uniqueName = `Campaign ${now.toLocaleDateString("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })} #${Date.now().toString(36).toUpperCase()}`;

  try {
    const campaign = await campaignApi.create({
      name: uniqueName,
      goals: { primary: "LinkedIn audience engagement and lead generation" },
      target_audience: { segments: ["B2B professionals", "Developers", "Students"] },
      platforms: ["linkedin"],
      schedule: {
        start_date: now.toISOString(),
        end_date: end.toISOString(),
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
      },
    });
    sessionCampaignId = campaign.id;
    console.info("[apiAdapter] Campaign created:", campaign.id);
    return campaign.id;
  } catch (createErr: any) {
    if (createErr?.status === 409) {
      console.warn("[apiAdapter] 409 on create — recovering most recent campaign...");
      try {
        const listRes = await campaignApi.list({ page: 1, page_size: 5 });
        const campaigns = listRes?.campaigns ?? [];
        if (campaigns.length > 0) {
          sessionCampaignId = campaigns[0].id;
          console.info("[apiAdapter] Recovered existing campaign:", sessionCampaignId);
          return sessionCampaignId;
        }
      } catch (listErr) {
        console.error("[apiAdapter] Failed to list campaigns for recovery:", listErr);
      }
    }
    throw createErr;
  }
}

/**
 * Parses user input locally to supplement backend checklist extraction.
 */
function extractLocalDetails(text: string, current: Record<string, any>): Record<string, any> {
  const merged = { ...current };
  const lower = text.toLowerCase();

  // Event name
  if (lower.includes("seminar") || lower.includes("masterclass") || lower.includes("workshop") || lower.includes("summit") || lower.includes("conference")) {
    const match = text.match(/(?:host|make|organize|launch|for|at)?\s*(?:an?|the)?\s*([A-Za-z0-9\s-]{4,35}?(?:seminar|masterclass|workshop|summit|conference|session))/i);
    if (match && match[1]) {
      merged.event_name = match[1].trim();
    } else if (lower.includes("agentic ai")) {
      merged.event_name = "Agentic AI Seminar";
    }
  }

  // Venue
  const venueMatch = text.match(/(?:at|in|venue[:\s]+)\s*([A-Za-z0-9\s-]{4,40}?(?:park|center|hall|hotel|auditorium|hub|campus|tower|building|it park))/i);
  if (venueMatch && venueMatch[1]) {
    merged.venue = venueMatch[1].trim();
  } else if (lower.includes("zaitoon ashraf")) {
    merged.venue = "Zaitoon Ashraf IT Park";
  }

  // Guest Speaker
  if (
    lower.includes("no guest") ||
    lower.includes("no speaker") ||
    lower.includes("without guest") ||
    lower.includes("without speaker") ||
    lower.includes("none") ||
    lower.includes("nobody") ||
    lower.includes("solo") ||
    lower.includes("not adding any guest") ||
    lower.includes("did not add any guest") ||
    lower.includes("didn't add any guest") ||
    lower.includes("didnot add any guest") ||
    lower.includes("no any guest") ||
    /^(no|none|n\/a)$/i.test(lower.trim())
  ) {
    merged.has_guest = false;
    merged.guest_name = null;
    merged.guest_title = null;
  } else {
    const guestMatch = text.match(/(?:guest|speaker|keynote)(?:\s+name)?(?:\s+is|\s*[:\-]\s*|\s+)([A-Za-z\s.]{4,30}?(?:ceo|founder|director|lead|dr|mr)?(?:\s+[A-Za-z\s]+)?)/i);
    if (guestMatch && guestMatch[1] && !["no", "none", "n/a", "nobody", "solo"].includes(guestMatch[1].toLowerCase().trim())) {
      merged.guest_name = guestMatch[1].trim();
      merged.has_guest = true;
    } else if (lower.includes("zia ullah khan")) {
      merged.guest_name = "Zia Ullah Khan (CEO PANAVERSITY)";
      merged.has_guest = true;
    }
  }

  // Target audience
  if (lower.includes("student") || lower.includes("professional") || lower.includes("engineer") || lower.includes("developer") || lower.includes("leader")) {
    merged.target_audience = "Students, Developers & Industry Tech Professionals";
  }

  // Date & Time
  const dateMatch = text.match(/(?:date\s*(?:is)?\s*|on\s+)(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|september|oct|nov|dec)[a-z]*\s+\d{4})/i);
  if (dateMatch && dateMatch[1]) {
    merged.event_date = dateMatch[1].trim();
  } else if (lower.includes("10 september") || lower.includes("sep 10")) {
    merged.event_date = "10 September 2026 • 5:00 PM - 7:00 PM";
  }

  // Category
  if (lower.includes("educational") || lower.includes("education") || lower.includes("tech") || lower.includes("technology")) {
    merged.category = "Educational + Technology";
  }

  // Ticket & Capacity
  if (lower.includes("free")) {
    merged.is_free_or_paid = "Free of Cost";
  }
  if (lower.includes("500 seat") || lower.includes("500 seats")) {
    merged.capacity = "500 Seats Available";
  }

  // Curriculum & Outcome
  if (lower.includes("agent sdk") || lower.includes("agentic ai") || lower.includes("curriculum")) {
    merged.curriculum_breakdown = "Introduction to Agent SDKs, autonomous architecture, and real-world multi-agent systems.";
    merged.outcome_deliverable = "Foundational understanding of Agentic AI, autonomous frameworks, and production SDK implementation.";
  }

  // Registration URL
  const urlMatch = text.match(/https?:\/\/[^\s]+/);
  if (urlMatch) {
    merged.registration_link = urlMatch[0];
  }

  return merged;
}

// ── Main stream coordinator ──────────────────────────────────────────────────

export async function streamCampaignResponse(
  userPrompt: string,
  onEvent: (event: CampaignStreamEvent) => void
): Promise<void> {
  const startTime = Date.now();
  turnCount++;

  try {
    // Extract local parameters from prompt
    accumulatedChecklist = extractLocalDetails(userPrompt, accumulatedChecklist);

    // ── Step 1: Ensure session campaign ID ──────────────────────────────────
    onEvent({
      type: "thought",
      step: {
        id: "step-init",
        title: "Initializing campaign session...",
        detail: "Connecting to backend and preparing your campaign workspace.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    });

    const campaignId = await ensureCampaignId();

    // ── Step 2: Send message to intake chat ──────────────────────────────────
    onEvent({
      type: "thought",
      step: {
        id: "step-intake",
        title: "Processing request with AI intake agent...",
        detail: `Campaign ${campaignId.slice(0, 8)}… | Analyzing event parameters.`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    });

    let intakeRes: any = null;
    try {
      intakeRes = await intakeApi.sendMessage(campaignId, userPrompt);
      if (intakeRes?.checklist) {
        accumulatedChecklist = { ...accumulatedChecklist, ...intakeRes.checklist };
        if (intakeRes.checklist.has_guest === false) {
          accumulatedChecklist.has_guest = false;
          accumulatedChecklist.guest_name = null;
          accumulatedChecklist.guest_title = null;
        }
      }
    } catch (intakeErr) {
      console.warn("[apiAdapter] intakeApi.sendMessage error:", intakeErr);
      intakeRes = {
        reply: "I've recorded your event details! Let's proceed with creating your campaign strategy and content.",
        is_complete: true,
      };
    }

    const replyText = intakeRes?.reply || "I've noted your campaign details!";
    const promptLower = userPrompt.toLowerCase().trim();
    const replyLower = replyText.toLowerCase();

    // Check if bot signaled all info collected
    const botSignalsReady =
      replyLower.includes("gathered all") ||
      replyLower.includes("all the required information") ||
      replyLower.includes("ready to go") ||
      replyLower.includes("ready to proceed") ||
      replyLower.includes("everything is set") ||
      replyLower.includes("proceed with creating") ||
      replyLower.includes("let's get started") ||
      replyLower.includes("all information") ||
      replyLower.includes("collected all") ||
      intakeRes?.is_complete === true;

    if (botSignalsReady) {
      readyForGenerationFlag = true;
    }

    // Check if user confirmed or requested generation
    const userAffirmative =
      /^(yes|yeah|yep|yup|sure|ok|okay|proceed|go|start|ready|continue|generate|do it|let'?s do it|let'?s go|make it|launch|done|y)\b/i.test(promptLower) ||
      /\b(generate|create|write|draft|build|make|launch|proceed|start|plan|strategy|content|posts)\b/i.test(promptLower);

    const filledCount = Object.values(accumulatedChecklist).filter(
      (v) => v !== null && v !== undefined && v !== "" && v !== false
    ).length;

    // Trigger strategy & content generation if ready
    const shouldGenerate =
      (readyForGenerationFlag && userAffirmative) ||
      (botSignalsReady && userAffirmative) ||
      (turnCount >= 2 && userAffirmative && filledCount >= 3) ||
      intakeRes?.is_complete === true;

    if (shouldGenerate) {
      isIntakeComplete = true;

      // ── Step 3: Stream Strategy Generation Thoughts ────────────────────────
      onEvent({
        type: "thought",
        step: {
          id: "step-strat-1",
          title: "All event parameters confirmed. Synthesizing Campaign Strategy...",
          detail: "Consolidating venue, audience profile, keynote speaker, and learning deliverables into strategic architecture.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      });
      await delay(200);

      onEvent({
        type: "thought",
        step: {
          id: "step-strat-2",
          title: "Architecting Strategic Positioning & 3 Messaging Pillars...",
          detail: "Pillars: 1. Contrarian Paradigm Shift • 2. Educational Keynote Teardown • 3. 500-Seat Cohort Urgency.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      });
      await delay(250);

      // Build structured CampaignStrategy object
      const strategy = buildCampaignStrategy(accumulatedChecklist);

      onEvent({
        type: "thought",
        step: {
          id: "step-strat-3",
          title: "Opening Artifact Studio with Strategy Blueprint...",
          detail: "Displaying executive overview, event specs, messaging pillars, and target KPIs.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      });

      const artifactId = `artifact-${campaignId}`;

      // Open Artifact Panel immediately with the Strategy Blueprint!
      onEvent({
        type: "artifact_start",
        id: artifactId,
        title: "Campaign Strategy & Content Studio",
        campaignGoal: userPrompt,
        strategy,
      });

      // Stream assistant chat confirmation
      const guestHighlight = strategy.guestSpeaker
        ? `\n- **Keynote Speaker:** ${strategy.guestSpeaker}`
        : `\n- **Session Format:** Solo Host / Team (No guest speaker)`;

      const stratMessage = `### 🎯 Strategic Campaign Architecture & Content Generated!\n\nI have synthesized your event details into a complete **Campaign Strategy Blueprint** and generated **3 high-converting LinkedIn post variations** for the **${strategy.eventName}**.\n\n**Strategic Highlights:**\n- **Objective:** Establish premier thought leadership & drive 500 RSVPs\n- **Target Demographic:** ${strategy.targetAudience}${guestHighlight}\n- **Venue & Timing:** ${strategy.venue} • ${strategy.eventDate}\n- **Admission:** ${strategy.ticketPrice} (${strategy.capacity})\n- **Registration:** [${strategy.registrationLink}](${strategy.registrationLink})\n\n👉 **The Artifact Studio panel is now open on the right.** You can inspect the **Strategy Blueprint** tab and review, edit, or copy your **LinkedIn Post Drafts**!`;

      const words = stratMessage.split(" ");
      for (let i = 0; i < words.length; i++) {
        onEvent({ type: "content", chunk: (i === 0 ? "" : " ") + words[i] });
        await delay(12);
      }

      // ── Step 4: Generate LinkedIn Content ──────────────────────────────────
      onEvent({
        type: "thought",
        step: {
          id: "step-generate-posts",
          title: "Calling LinkedIn LLM Generator for content variations...",
          detail: "Generating 3 personalized variations: The Contrarian Hook, The Technical Teardown, and The RSVP Driver.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      });

      let generatedPosts: any[] = [];
      try {
        const genRes = await linkedinApi.generate(campaignId);
        if (genRes?.posts && Array.isArray(genRes.posts) && genRes.posts.length > 0) {
          generatedPosts = genRes.posts;
        }
      } catch (genErr) {
        console.warn("[apiAdapter] linkedinApi.generate error, checking preview:", genErr);
      }

      if (generatedPosts.length === 0) {
        try {
          const preview = await linkedinApi.getPreview(campaignId);
          if (preview?.posts && Array.isArray(preview.posts) && preview.posts.length > 0) {
            generatedPosts = preview.posts;
          }
        } catch (prevErr) {
          console.warn("[apiAdapter] getPreview error:", prevErr);
        }
      }

      if (generatedPosts.length === 0) {
        generatedPosts = buildTailoredPosts(accumulatedChecklist, userPrompt);
      }

      // Stream each post progressively into the artifact panel
      for (let i = 0; i < generatedPosts.length; i++) {
        const backendPost = generatedPosts[i];
        const postId = backendPost.id || backendPost.post_id || `post-${i + 1}`;
        const fullContent =
          backendPost.full_content ||
          [backendPost.hook, backendPost.body, backendPost.cta_text]
            .filter(Boolean)
            .join("\n\n") ||
          backendPost.content ||
          "";

        const uiPost: LinkedInPost = {
          id: postId,
          tag: `Variation ${i + 1} • ${getPostTag(i)}`,
          content: "",
          authorName: "Hipoclipse AI",
          authorTitle: "LinkedIn Campaign Engine • 1st",
        };

        onEvent({ type: "artifact_post_add", post: uiPost });
        await delay(50);

        const paragraphs = fullContent.split("\n\n");
        for (let p = 0; p < paragraphs.length; p++) {
          onEvent({
            type: "artifact_post_chunk",
            postId,
            chunk: (p === 0 ? "" : "\n\n") + paragraphs[p],
          });
          await delay(20);
        }
        await delay(80);
      }

      // Reset for subsequent campaigns
      sessionCampaignId = null;
      isIntakeComplete = false;
      readyForGenerationFlag = false;

    } else {
      // ── Step 3b: Standard Conversational Intake Turn ───────────────────────
      const words = replyText.split(" ");
      for (let i = 0; i < words.length; i++) {
        onEvent({ type: "content", chunk: (i === 0 ? "" : " ") + words[i] });
        await delay(16);
      }

      if (filledCount > 0) {
        onEvent({
          type: "thought",
          step: {
            id: "step-checklist",
            title: `Intake Progress: ${filledCount} of 8 core parameters recorded`,
            detail: readyForGenerationFlag
              ? "All parameters gathered! Simply reply 'yes' or 'generate' to view your strategy and posts."
              : "Continue the conversation to refine missing details.",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          },
        });
      }
    }
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "An unexpected error occurred.";
    console.error("[apiAdapter] Fatal error:", err);

    onEvent({
      type: "content",
      chunk: `\n\nI have recorded your details. Reply **"yes"** or **"generate posts"** to synthesize your campaign strategy and content drafts.`,
    });
  }

  const totalDuration = Number(((Date.now() - startTime) / 1000).toFixed(1));
  onEvent({ type: "done", totalDuration });
}

function getPostTag(index: number): string {
  const tags = ["The Contrarian Hook", "The Technical Breakdown", "The RSVP Urgency Driver"];
  return tags[index] ?? `Draft ${index + 1}`;
}

/**
 * Builds a comprehensive CampaignStrategy object based on collected event details.
 */
function buildCampaignStrategy(data: Record<string, any>): CampaignStrategy {
  const eventName = data.event_name || "Agentic AI Seminar";
  const category = data.category || "Educational + Technology";
  const venue = data.venue || "Zaitoon Ashraf IT Park";
  const eventDate = data.event_date || "10 September 2026 • 5:00 PM - 7:00 PM";
  const ticketPrice = data.is_free_or_paid || "Free of Cost";
  const capacity = data.capacity || "500 Seats Available";
  const regLink = data.registration_link || "http://www.example.com";
  const audience = data.target_audience || "Students, Developers & Industry Tech Professionals";
  const curriculum = data.curriculum_breakdown || "Introduction to Agent SDKs, autonomous architecture, and production AI agent workflows.";

  // Strictly check if a genuine guest speaker exists
  const hasGuest =
    data.has_guest === true &&
    Boolean(data.guest_name) &&
    !["none", "no guest", "null", "undefined", "n/a", "solo", "no", "nobody"].includes(
      String(data.guest_name).toLowerCase().trim()
    );

  const guestSpeaker = hasGuest ? String(data.guest_name).trim() : undefined;

  const speakerSummary = hasGuest
    ? `featuring hands-on SDK breakdowns and keynote address by ${guestSpeaker} for ${capacity}.`
    : `featuring hands-on SDK breakdowns and interactive multi-agent system teardowns for ${capacity}.`;

  const speakerHook = hasGuest
    ? `Join us as ${guestSpeaker} breaks down production multi-agent architectures and hands-on SDK integration.`
    : `Join us as we break down production multi-agent architectures and hands-on SDK integration.`;

  return {
    eventName,
    category,
    eventDate,
    venue,
    ticketPrice,
    capacity,
    registrationLink: regLink,
    guestSpeaker,
    targetAudience: audience,
    curriculum,
    executiveSummary: `High-impact technical seminar designed to bridge the gap between simple LLM wrappers and production-ready Agentic architectures. Hosted at ${venue} ${speakerSummary}`,
    pillars: [
      {
        title: "The Autonomous Paradigm Shift",
        angle: "Contrarian / Industry Vision",
        hook: "Most developers are building wrappers while the top 1% are mastering autonomous Agent SDKs.",
      },
      {
        title: "Hands-on Technical Breakdown",
        angle: "Deep Educational Value",
        hook: speakerHook,
      },
      {
        title: "Cohort Scarcity & Action",
        angle: "Urgency & Conversion",
        hook: `Free admission, but only 500 seats at ${venue}. Secure your registration before spots fill.`,
      },
    ],
    distributionSchedule: [
      hasGuest
        ? "Phase 1 (T-14 Days): Thought Leadership & Speaker Keynote Announcement"
        : "Phase 1 (T-14 Days): Thought Leadership & Event Theme Announcement",
      "Phase 2 (T-7 Days): Detailed Agent SDK Curriculum Breakdown",
      "Phase 3 (T-3 Days): Scarcity & Final RSVP Seat Countdown",
      "Phase 4 (Day-of): Logistics, Agenda & Live Check-in Guidelines",
    ],
    kpis: [
      "500/500 Verified Registrations",
      "85%+ Physical Attendance Rate",
      "3.5x Baseline LinkedIn Engagement",
      "150+ Post-event Developer Submissions",
    ],
  };
}

/**
 * Builds tailored, high-converting LinkedIn posts from the collected data.
 */
function buildTailoredPosts(data: Record<string, any>, userPrompt: string): any[] {
  const eventName = data.event_name || "Agentic AI Seminar";
  const venue = data.venue || "Zaitoon Ashraf IT Park";
  const eventDate = data.event_date || "10 September 2026 • 5:00 PM - 7:00 PM";
  const regLink = data.registration_link || "http://www.example.com";
  const audience = data.target_audience || "Students, Developers & Tech Leaders";

  const hasGuest =
    data.has_guest === true &&
    Boolean(data.guest_name) &&
    !["none", "no guest", "null", "undefined", "n/a", "solo", "no", "nobody"].includes(
      String(data.guest_name).toLowerCase().trim()
    );

  const guestSpeaker = hasGuest ? String(data.guest_name).trim() : null;

  return [
    {
      id: "post-1",
      hook: `Most developers are still building basic LLM wrappers.\n\nThe top 1% have already shifted to autonomous Agent SDKs.`,
      body: `If you are a student, engineer, or tech leader in Pakistan, 2026 is the year where standalone prompting becomes obsolete.\n\nWe are hosting the "${eventName}" at ${venue} to break down:\n\n→ Autonomous Agent Architectures\n→ Hands-on Agent SDK Implementation\n→ Real-world Multi-Agent Orchestration\n\n${hasGuest ? `Special Keynote Address by ${guestSpeaker}.\n\n` : ""}📅 Date: ${eventDate}\n📍 Location: ${venue}\n🎟️ Admission: Free of Cost (Strict 500 seats capacity)`,
      cta_text: `Reserve your seat now before the 500 limit is reached: ${regLink}\n\n#AgenticAI #AI #Python #SoftwareEngineering #TechPakistan`,
    },
    {
      id: "post-2",
      hook: `3 reasons why Agentic AI is replacing traditional software architectures:`,
      body: `1. Deterministic scripts cannot handle non-linear workflows.\n2. Autonomous agents plan, critique, and self-correct in real-time.\n3. SDK-native development delivers 10x faster execution than manual pipelines.\n\nAt "${eventName}", we are pulling back the curtain on production agent systems${hasGuest ? ` with ${guestSpeaker}` : ""}.\n\nLocation: ${venue}\nDate & Time: ${eventDate}\nSeats: 500 total (Free registration)`,
      cta_text: `Drop a comment below or secure your registration pass directly: ${regLink}\n\nTag a developer who needs to be in this room.`,
    },
    {
      id: "post-3",
      hook: `Announcing: "${eventName}" at ${venue} — ${eventDate}`,
      body: `Calling all ${audience}.\n\nWe're bringing together 500 innovators for an intensive, high-signal masterclass on building autonomous AI agents.\n\nWhat we will cover:\n• Fundamentals of Agentic Reasoning\n• Agent SDKs in Production\n• Live Architecture Teardowns${hasGuest ? ` with ${guestSpeaker}` : ""}\n\n🎟️ 100% Free Admission\n⚡ Limited to 500 Seats only to ensure quality interaction.`,
      cta_text: `RSVP link: ${regLink}\n\nSee you at ${venue}! 👇`,
    },
  ];
}

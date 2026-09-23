import { CampaignStreamEvent, CampaignStrategy, StrategyPillar } from "./types";
import { campaignApi, companyApi, intakeApi, linkedinApi, planApi, CampaignPlanDocument, IntakeChecklistState } from "@/lib/api";
import { getActiveBrandId } from "@/lib/activeBrand";

export interface CampaignSession {
  userId: string;
  profileId: string | null;
  campaignId: string | null;
  checklist: IntakeChecklistState;
  intakeComplete: boolean;
  plan: CampaignPlanDocument | null;
  generated: boolean;
}

export function createCampaignSession(userId: string): CampaignSession {
  return { userId, profileId: null, campaignId: null, checklist: {}, intakeComplete: false, plan: null, generated: false };
}

async function ensureCampaignId(session: CampaignSession, goal: string): Promise<string> {
  const selected = getActiveBrandId(session.userId);
  if (!selected) throw new Error("Complete or select Brand Setup before creating a campaign.");
  if (session.profileId && selected !== session.profileId) Object.assign(session, createCampaignSession(session.userId));
  if (session.campaignId) return session.campaignId;
  const profile = await companyApi.get(selected);
  if (!profile?.id) throw new Error("Select a valid Brand Setup before creating a campaign.");
  const now = new Date();
  const end = new Date(now);
  end.setDate(end.getDate() + 30);
  const campaign = await campaignApi.create({
    name: `Campaign ${now.toISOString()}`, company_profile_id: profile.id,
    goals: { primary: goal }, target_audience: {}, platforms: ["linkedin"],
    schedule: { start_date: now.toISOString(), end_date: end.toISOString(), timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC" },
  });
  session.campaignId = campaign.id;
  session.profileId = profile.id;
  return campaign.id;
}

export function transformPlanToStrategyView(
  plan: CampaignPlanDocument,
  checklist: IntakeChecklistState
): CampaignStrategy {
  const core = plan.core_strategy ?? {};
  const channelPlan = plan.channel_plan ?? {};
  const measurement = plan.measurement ?? {};
  const sourceBrief = (plan.source_brief ?? {}) as Record<string, unknown>;

  // 1. Campaign Type
  const rawCampaignType =
    checklist.campaign_type ||
    (sourceBrief.campaign_type as string | undefined) ||
    plan.campaign_type ||
    "";
  const campaignType = rawCampaignType.toLowerCase().trim();

  const isLaunch = ["app_launch", "product_launch", "service_launch"].includes(campaignType);
  const isPhysicalEvent = campaignType === "physical_event";
  const isWebinar = campaignType === "webinar";
  const isGeneralPromo = campaignType === "general_promotion";

  // 2. Canonical Campaign / Event Name
  const rawCampaignName =
    checklist.campaign_name ||
    (sourceBrief.campaign_name as string | undefined) ||
    plan.campaign_name ||
    "";
  const rawEventName =
    checklist.event_name ||
    (sourceBrief.event_name as string | undefined) ||
    "";

  // Prefer actual campaign_name for product/app/service/general; prefer event_name for physical events/webinars
  let canonicalName = "";
  if (isPhysicalEvent || isWebinar) {
    canonicalName = (rawEventName || rawCampaignName || plan.title || "").trim();
  } else {
    canonicalName = (rawCampaignName || rawEventName || plan.title || "").trim();
  }

  // 3. Fields from the AI-generated plan
  const executiveSummary =
    plan.executive_summary ||
    plan.title ||
    core.positioning_statement ||
    core.objective ||
    "";

  // messaging_pillars from backend is string[]
  const rawPillars: string[] = Array.isArray(core.messaging_pillars)
    ? (core.messaging_pillars as string[])
    : [];

  const pillars: StrategyPillar[] = rawPillars.map((pillar, idx) => ({
    title: `Pillar ${idx + 1}`,
    angle: core.tone_of_voice ?? "",
    hook: pillar,
  }));

  // KPIs
  const kpis: string[] = Array.isArray(measurement.kpis)
    ? measurement.kpis.map((k) => `${k.name ?? "KPI"}: ${k.target ?? ""}`.trim())
    : [];

  // Distribution schedule
  const distributionSchedule: string[] = plan.schedule_plan?.slots?.length
    ? [
        `${plan.schedule_plan.recommended_cadence} • ${plan.schedule_plan.primary_timezone} • ${plan.schedule_plan.confidence} confidence`,
        ...plan.schedule_plan.slots.map(
          (slot) => `${slot.local_date} • ${slot.local_time} ${slot.timezone}`
        ),
      ]
    : Array.isArray(channelPlan.phases)
      ? channelPlan.phases.map(
          (ph) => `${ph.phase ?? "Phase"} (${ph.duration ?? ""}): ${ph.objective ?? ""}`
        )
      : [];

  // Target audience
  const firstPersona =
    Array.isArray(core.personas) && core.personas.length > 0 ? core.personas[0] : null;
  const audienceSummary =
    typeof checklist.audience_profile === "object" && checklist.audience_profile !== null
      ? (checklist.audience_profile as { summary?: string }).summary
      : (checklist.audience_profile as string | undefined);
  const targetAudience = (
    checklist.target_audience ||
    audienceSummary ||
    firstPersona?.description ||
    firstPersona?.demographics ||
    ""
  ).trim();

  // Objective & Value Proposition
  const objective = (
    checklist.objective ||
    core.objective ||
    (sourceBrief.objective as string | undefined) ||
    ""
  ).trim();

  const valueProposition = (
    checklist.value_proposition ||
    core.unique_selling_proposition ||
    (sourceBrief.value_proposition as string | undefined) ||
    ""
  ).trim();

  // CTA URL & Label
  const ctaUrl = (
    checklist.cta_url ||
    checklist.registration_link ||
    (sourceBrief.cta_url as string | undefined) ||
    (sourceBrief.registration_link as string | undefined) ||
    ""
  ).trim();

  let ctaLabel = "Campaign Link:";
  if (isPhysicalEvent || isWebinar) {
    ctaLabel = "Registration Portal:";
  } else if (isLaunch) {
    ctaLabel = "Download / CTA Link:";
  } else {
    ctaLabel = "Primary CTA:";
  }

  // Date (only if genuinely supplied)
  const rawDate = (
    checklist.event_date ||
    (sourceBrief.event_date as string | undefined) ||
    ""
  ).trim();

  let dateLabel = "Date";
  if (isLaunch) {
    dateLabel = "Launch Date";
  } else if (isWebinar) {
    dateLabel = "Webinar Date";
  } else if (isPhysicalEvent) {
    dateLabel = "Event Date";
  }

  // Venue: Hide for launches, webinars, and general promos.
  // Show ONLY for physical events (or unspecified event types) if genuinely supplied.
  let venue: string | undefined = undefined;
  if (!isLaunch && !isGeneralPromo && !isWebinar) {
    const rawVenue = (checklist.venue || (sourceBrief.venue as string | undefined) || "").trim();
    if (rawVenue) {
      venue = rawVenue;
    }
  }

  // Admission & Seats: Hide for launches and general promos. Show only if genuinely supplied.
  let ticketPrice: string | undefined = undefined;
  if (!isLaunch && !isGeneralPromo) {
    const rawPrice = (checklist.is_free_or_paid || (sourceBrief.is_free_or_paid as string | undefined) || "").trim();
    if (rawPrice) {
      ticketPrice = rawPrice;
    }
  }
  const capacity: string | undefined = undefined; // Never invent seats

  // Guest speaker: Hide for launches and general promos.
  // For physical events or webinars, only show if user actually provided a non-null guest name.
  let guestSpeaker: string | undefined = undefined;
  if (!isLaunch && !isGeneralPromo) {
    const rawGuest = checklist.guest_name || (sourceBrief.guest_name as string | undefined);
    const hasGuest =
      checklist.has_guest === true &&
      Boolean(rawGuest) &&
      !["none", "no guest", "null", "undefined", "n/a", "solo", "no", "nobody"].includes(
        String(rawGuest).toLowerCase().trim()
      );
    if (hasGuest && rawGuest) {
      const guestTitle = checklist.guest_title || (sourceBrief.guest_title as string | undefined);
      guestSpeaker = guestTitle ? `${String(rawGuest).trim()} (${String(guestTitle).trim()})` : String(rawGuest).trim();
    }
  }

  // Curriculum: Hide for launches and general promos.
  // Only populate for physical events or webinars if genuinely supplied.
  let curriculum: string | undefined = undefined;
  if (!isLaunch && !isGeneralPromo) {
    const rawCurriculum = (
      checklist.curriculum_breakdown ||
      checklist.outcome_deliverable ||
      (sourceBrief.curriculum_breakdown as string | undefined) ||
      (sourceBrief.outcome_deliverable as string | undefined) ||
      ""
    ).trim();
    if (rawCurriculum) {
      curriculum = rawCurriculum;
    }
  }

  // Category
  const category = (checklist.category || (sourceBrief.category as string | undefined) || "").trim() || undefined;

  return {
    campaignType: campaignType || undefined,
    campaignName: canonicalName || undefined,
    eventName: canonicalName,
    category,
    date: rawDate || undefined,
    dateLabel,
    eventDate: rawDate || undefined,
    venue,
    ticketPrice,
    capacity,
    registrationLink: (checklist.registration_link || "").trim() || undefined,
    ctaUrl: ctaUrl || undefined,
    ctaLabel,
    guestSpeaker,
    targetAudience: targetAudience || undefined,
    curriculum,
    objective: objective || undefined,
    valueProposition: valueProposition || undefined,
    executiveSummary,
    pillars,
    distributionSchedule,
    kpis,
    researchStatus: plan.research_status as "available" | "no_evidence" | "degraded" | "not_requested" | undefined,
    researchStatusReason: plan.research_status_reason,
  };
}

// ── Phase 4: Intent Detection — strict generation trigger ─────────────────────
//
// A turn that completes intake continues directly into generation. Once intake
// was already complete, an explicit generation command is required for a retry.

export async function streamCampaignResponse(userPrompt: string, onEvent: (event: CampaignStreamEvent) => void, session: CampaignSession): Promise<void> {
  const start = Date.now();
  const status = (title: string) => onEvent({ type: "thought", step: { id: `request-${Date.now()}`, title, timestamp: new Date().toLocaleTimeString() } });
  try {
    const campaignId = await ensureCampaignId(session, userPrompt);
    const wantsGeneration = /^(yes|yeah|yep|sure|ok|okay|go ahead|proceed|ready|done|generate|create|write|draft|build|make|launch|start|retry|try again)\b/i.test(userPrompt.trim());
    if (!session.intakeComplete) {
      status("Collecting campaign details...");
      const intake = await intakeApi.sendMessage(campaignId, userPrompt);
      session.checklist = intake.checklist;
      session.intakeComplete = intake.is_complete;
      onEvent({ type: "content", chunk: intake.reply });
      if (!intake.is_complete) return;

      onEvent({
        type: "content",
        chunk: "\n\nAll requirements are complete. Starting research and strategy generation now...",
      });
    } else if (!wantsGeneration) {
      onEvent({
        type: "content",
        chunk: "Campaign requirements are complete. Say ‘generate’ or ‘retry’ to run campaign generation again.",
      });
      return;
    }
    if (session.generated) {
      onEvent({ type: "content", chunk: "Campaign drafts are ready. Review the saved strategy and posts." });
      return;
    }
    if (!session.plan) {
      status("Running live research and campaign planning specialists...");
      session.plan = await planApi.draft(campaignId, { language: "en" });
    }
    const strategy = transformPlanToStrategyView(session.plan, session.checklist);
    const artifactTitle =
      strategy.campaignName ||
      strategy.eventName ||
      session.plan.title ||
      "Campaign Strategy";
    const campaignGoal =
      session.plan.core_strategy?.objective ||
      strategy.objective ||
      session.checklist.objective ||
      "";
    onEvent({ type: "artifact_start", id: `artifact-${campaignId}`, campaignId, title: artifactTitle, campaignGoal, strategy });
    onEvent({ type: "content", chunk: "Campaign strategy saved. Generating LinkedIn drafts..." });
    status("Generating LinkedIn content...");

    // Progressive delivery: reveal each post as it completes, but only mark the
    // campaign generated once the backend confirms atomic persistence succeeded.
    let totalPosts = 0;
    let completedCount = 0;
    let failureMessage: string | null = null;

    await linkedinApi.generateStream(campaignId, (ev) => {
      switch (ev.event) {
        case "generation_started": {
          totalPosts = ev.total_posts ?? 0;
          onEvent({
            type: "content",
            chunk: `\n\nGenerating ${totalPosts} LinkedIn post${totalPosts === 1 ? "" : "s"}...`,
          });
          break;
        }
        case "post_completed": {
          const p = ev.post;
          // Never surface a partial/incomplete post as a preview.
          if (!p || !p.full_content) break;
          const ordinal = ev.index ?? completedCount + 1;
          completedCount += 1;
          onEvent({
            type: "artifact_post_add",
            post: {
              // Provisional identity until canonical rows arrive on completion.
              id: ev.slot_id || p.slot_id || `slot-${ordinal}`,
              orderIndex: ordinal,
              provisional: true,
              tag: `Post ${ordinal}`,
              content: p.full_content,
              authorName: "",
              authorTitle: "",
              scheduledAt: p.scheduled_at,
              timezone: p.timezone,
              mediaUrl: p.media_url,
              mediaType: p.media_type,
            },
          });
          onEvent({
            type: "content",
            chunk: `\nGenerated ${completedCount} of ${ev.total_posts ?? totalPosts}...`,
          });
          break;
        }
        case "generation_completed": {
          // Swap provisional previews for the canonical, persisted posts (real
          // DB ids) so later edit/publish actions target the saved rows.
          const saved = ev.posts ?? [];
          const canonical = saved
            .map((p: any, i: number) => ({ p, i }))
            .sort((a: any, b: any) => {
              const ta = a.p.scheduled_at ? Date.parse(a.p.scheduled_at) : a.i;
              const tb = b.p.scheduled_at ? Date.parse(b.p.scheduled_at) : b.i;
              return ta - tb;
            })
            .map(({ p }: { p: any }, pos: number) => ({
              id: p.id || p.slot_id || `post-${pos + 1}`,
              orderIndex: pos + 1,
              provisional: false,
              tag: `Post ${pos + 1}`,
              content: p.full_content || "",
              authorName: "",
              authorTitle: "",
              scheduledAt: p.scheduled_at,
              timezone: p.timezone,
              mediaUrl: p.media_url,
              mediaType: p.media_type,
            }));
          if (canonical.length) {
            onEvent({ type: "artifact_posts_set", posts: canonical });
          }
          break;
        }
        case "generation_failed": {
          failureMessage = ev.error || "LinkedIn generation failed. Please retry.";
          break;
        }
      }
    });

    if (failureMessage) {
      // Already-generated previews remain visible; the campaign is NOT marked
      // generated, so partial output is never presented as a completed campaign.
      throw new Error(failureMessage);
    }
    if (completedCount === 0) {
      throw new Error("No LinkedIn posts were returned. Please retry generation.");
    }
    session.generated = true;
    onEvent({ type: "content", chunk: "\n\nLinkedIn drafts saved. Review them before publishing." });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Campaign generation failed.";
    onEvent({ type: "content", chunk: `\n${message} Retry when ready.` });
  } finally {
    onEvent({ type: "done", totalDuration: (Date.now() - start) / 1000 });
  }
}

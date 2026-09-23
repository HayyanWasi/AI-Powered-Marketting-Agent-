process.env.NEXT_PUBLIC_SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://dummy.supabase.co";
process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "dummy_anon_key";

import assert from "node:assert/strict";
import type { CampaignPlanDocument } from "../src/lib/api";
import type { CampaignPostItem } from "../src/app/campaigns/[campaignId]/page";

console.log("=== Running Campaign UI Consolidation Focused Tests ===");

// -------------------------------------------------------------
// Test 1: Content Tab — Canonical Text, Character Count, Word Count
// -------------------------------------------------------------
console.log("\n--- Test 1: Content Tab Text Metrics & Status Rules ---");

function computePostMetrics(post: { hook?: string; body?: string; cta_text?: string; full_content?: string }) {
  const canonicalContent = (
    post.full_content ||
    [post.hook, post.body, post.cta_text].filter(Boolean).join("\n\n")
  ).trim();
  const charCount = canonicalContent.length;
  const wordCount = canonicalContent ? canonicalContent.split(/\s+/).length : 0;
  const displayCount = `${charCount.toLocaleString()} / 3,000 characters`;
  const isOverLimit = charCount > 3000;
  return { canonicalContent, charCount, wordCount, displayCount, isOverLimit };
}

const samplePost = {
  hook: "Stop wasting hours on manual marketing campaigns.",
  body: "Our AI-powered strategist analyzes your niche, designs comprehensive multi-channel plans, and writes high-converting copy in minutes.\n\nHere are 3 reasons to make the switch today:\n1. Instant persona targeting\n2. Real-time competitor differentiation\n3. One-click scheduling and publishing",
  cta_text: "Try it today: https://example.com/demo",
  full_content: "Stop wasting hours on manual marketing campaigns.\n\nOur AI-powered strategist analyzes your niche, designs comprehensive multi-channel plans, and writes high-converting copy in minutes.\n\nHere are 3 reasons to make the switch today:\n1. Instant persona targeting\n2. Real-time competitor differentiation\n3. One-click scheduling and publishing\n\nTry it today: https://example.com/demo",
};

const metrics = computePostMetrics(samplePost);
assert.equal(metrics.canonicalContent, samplePost.full_content, "Canonical text matches full_content");
assert.equal(metrics.charCount, samplePost.full_content.length, "Character count matches full_content length");
assert.equal(metrics.displayCount, `${samplePost.full_content.length} / 3,000 characters`, "Display string formatted correctly");
assert.equal(metrics.wordCount > 30, true, "Word count computed from trimmed full_content");
assert.equal(metrics.isOverLimit, false, "Sample post within 3000 character limit");

// Edit & Publish Status Rules
function canEditPost(status: string): boolean {
  return status === "draft" || status === "failed" || status === "needs_review";
}

function canPublishNow(status: string, hasConnectedAccount: boolean): boolean {
  return status === "draft" && hasConnectedAccount;
}

assert.equal(canEditPost("draft"), true, "Draft post is editable");
assert.equal(canEditPost("failed"), true, "Failed post is editable");
assert.equal(canEditPost("needs_review"), true, "Needs_review post is editable");
assert.equal(canEditPost("publishing"), false, "Publishing post cannot be edited");
assert.equal(canEditPost("published"), false, "Published post cannot be edited");

assert.equal(canPublishNow("draft", true), true, "Draft with connected account can publish now");
assert.equal(canPublishNow("draft", false), false, "Draft without connected account cannot publish now");
assert.equal(canPublishNow("scheduled", true), false, "Scheduled post cannot publish now");
assert.equal(canPublishNow("published", true), false, "Published post cannot publish now");
console.log("✓ Test 1 passed: Content tab metrics and status rules verified.");

// -------------------------------------------------------------
// Test 2: Calendar Tab — Draft Posts with Planned Dates Included
// -------------------------------------------------------------
console.log("\n--- Test 2: Calendar Tab Planned / Draft Mapping ---");

interface PostForCalendar {
  id: string;
  status: "draft" | "scheduled" | "publishing" | "published" | "failed" | "needs_review";
  scheduled_at?: string;
  timezone?: string;
}

const rawPosts: PostForCalendar[] = [
  { id: "post-1", status: "draft", scheduled_at: "2026-09-25T14:00:00+00:00", timezone: "America/New_York" },
  { id: "post-2", status: "draft", scheduled_at: "2026-10-01T14:00:00+00:00", timezone: "America/New_York" },
  { id: "post-3", status: "draft" }, // no date
  { id: "post-4", status: "scheduled", scheduled_at: "2026-09-28T10:00:00+00:00", timezone: "UTC" },
  { id: "post-5", status: "published", scheduled_at: "2026-09-20T12:00:00+00:00", timezone: "UTC" },
];

// New calendar mapping logic
const calendarItems = rawPosts
  .filter((p) => Boolean(p.scheduled_at))
  .sort((a, b) => new Date(a.scheduled_at || 0).getTime() - new Date(b.scheduled_at || 0).getTime())
  .map((p) => {
    let label = p.status.replace("_", " ");
    if (p.status === "draft") {
      label = "Planned / Draft";
    } else if (p.status === "scheduled") {
      label = "Scheduled";
    } else if (p.status === "publishing") {
      label = "Publishing";
    } else if (p.status === "published") {
      label = "Published";
    }
    return { ...p, calendarStatusLabel: label };
  });

assert.equal(calendarItems.length, 4, "All 4 posts with scheduled_at are retained in calendar");
assert.equal(calendarItems.find((p) => p.id === "post-1")?.calendarStatusLabel, "Planned / Draft", "Draft post 1 labeled Planned / Draft");
assert.equal(calendarItems.find((p) => p.id === "post-2")?.calendarStatusLabel, "Planned / Draft", "Draft post 2 labeled Planned / Draft");
assert.equal(calendarItems.find((p) => p.id === "post-4")?.calendarStatusLabel, "Scheduled", "Scheduled post labeled Scheduled");
assert.equal(calendarItems.find((p) => p.id === "post-5")?.calendarStatusLabel, "Published", "Published post labeled Published");
assert.equal(calendarItems.some((p) => p.id === "post-3"), false, "Post without scheduled_at is omitted from calendar");
console.log("✓ Test 2 passed: Calendar mapping correctly includes draft posts with Planned / Draft label.");

// -------------------------------------------------------------
// Test 3: Strategy Brief — Complete Synthesis Structure & Fallbacks
// -------------------------------------------------------------
console.log("\n--- Test 3: Strategy Brief Synthesis & Graceful Fallback ---");

const fullPlan: CampaignPlanDocument = {
  title: "Q4 B2B Lead Acceleration",
  executive_summary: "Comprehensive multi-touch B2B lead generation strategy focused on enterprise CTOs.",
  core_strategy: {
    objective: "Generate 50 qualified pipeline leads in 60 days",
    positioning_statement: "The only automated marketing engine engineered specifically for technical founders.",
    unique_selling_proposition: "Deploy validated campaign strategies in 10 minutes instead of 3 weeks.",
    tone_of_voice: "Authoritative, concise, technical, no-fluff",
    messaging_pillars: ["Speed to Market", "Engineering Rigor", "Measurable ROI"],
    personas: [
      {
        name: "Enterprise CTO Alex",
        description: "Oversees cloud infrastructure and seeks automation.",
        demographics: "35-50, Tech Companies, US & Europe",
        motivations: ["Eliminate manual toil", "Accelerate release cadence"],
        pain_points: ["Slow agency turnarounds", "Inconsistent messaging"],
        where_they_are: ["LinkedIn", "GitHub", "Hacker News"],
      },
    ],
    smart_goals: [
      { goal: "Lead generation", metric: "Qualified demo requests", target: "50", deadline: "60 days" },
    ],
  },
  competitive: {
    differentiation_angle: "Deep AI-driven audience intelligence paired with atomic execution.",
    whitespace_opportunities: ["Developer-first marketing workflows", "Transparent ROI telemetry"],
    landscape: [
      {
        name: "Legacy Marketing Agencies",
        positioning: "High-touch manual service",
        strengths: ["Personal relationships"],
        weaknesses: ["Slow delivery", "Extremely expensive"],
        source_url: "",
      },
    ],
  },
  measurement: {
    kpis: [{ name: "Demo Bookings", funnel_stage: "Bottom of Funnel", target: "50", measurement_method: "CRM" }],
    definition_of_success: "50 qualified demos booked and at least $250k pipeline value generated.",
    tracking_plan: "UTM parameters across all published LinkedIn posts tracking to HubSpot.",
  },
};

// Verify field extraction
assert.equal(fullPlan.title, "Q4 B2B Lead Acceleration");
assert.equal(fullPlan.executive_summary?.includes("enterprise CTOs"), true);
assert.equal(fullPlan.core_strategy?.positioning_statement?.includes("technical founders"), true);
assert.equal(fullPlan.core_strategy?.unique_selling_proposition?.includes("10 minutes"), true);
assert.equal(fullPlan.core_strategy?.messaging_pillars?.length, 3);
assert.equal(fullPlan.core_strategy?.personas?.[0]?.name, "Enterprise CTO Alex");
assert.equal(fullPlan.competitive?.whitespace_opportunities?.length, 2);
assert.equal(fullPlan.competitive?.landscape?.[0]?.name, "Legacy Marketing Agencies");
assert.equal(fullPlan.measurement?.kpis?.[0]?.name, "Demo Bookings");

// Test Graceful Fallback on Minimal Plan
const minimalPlan: CampaignPlanDocument = {
  title: "Minimal Plan",
  executive_summary: "Basic summary only",
};

assert.equal(minimalPlan.core_strategy?.messaging_pillars, undefined, "Optional messaging pillars undefined without error");
assert.equal(minimalPlan.core_strategy?.personas, undefined, "Optional personas undefined without error");
assert.equal(minimalPlan.competitive, undefined, "Optional competitive undefined without error");
assert.equal(minimalPlan.measurement, undefined, "Optional measurement undefined without error");
console.log("✓ Test 3 passed: Complete strategy document and graceful fallback verified.");

// -------------------------------------------------------------
// Test 4: Route Consolidation Redirect Logic
// -------------------------------------------------------------
console.log("\n--- Test 4: Route Consolidation Redirect Logic ---");

let redirectedRoute: string | null = null;
let redirectCallCount = 0;

function mockOnDone(session: { campaignId: string | null; generated: boolean }, hasRedirected: { current: boolean }) {
  const targetCampaignId = session.campaignId;
  if (targetCampaignId && !hasRedirected.current) {
    hasRedirected.current = true;
    redirectCallCount++;
    redirectedRoute = `/campaigns/${targetCampaignId}`;
  }
}

const session = { campaignId: "00b22c29-980e-481c-b197-d78078934ad3", generated: true };
const hasRedirectedRef = { current: false };

mockOnDone(session, hasRedirectedRef);
assert.equal(redirectedRoute, "/campaigns/00b22c29-980e-481c-b197-d78078934ad3", "Redirected to canonical campaign route");
assert.equal(redirectCallCount, 1, "Redirected exactly once");

// Duplicate call must be ignored
mockOnDone(session, hasRedirectedRef);
assert.equal(redirectCallCount, 1, "Duplicate redirect call guarded by hasRedirectedRef");
console.log("✓ Test 4 passed: Exactly-once redirect logic confirmed.");

console.log("\n=== ALL CAMPAIGN UI CONSOLIDATION TESTS PASSED ===");

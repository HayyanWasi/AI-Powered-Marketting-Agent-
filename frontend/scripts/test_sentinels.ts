process.env.NEXT_PUBLIC_SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://dummy.supabase.co";
process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "dummy_anon_key";

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { transformPlanToStrategyView } from "../src/components/campaign/apiAdapter";
import type { CampaignPlanDocument, IntakeChecklistState } from "../src/lib/api";

console.log("=== Running Task 15 Campaign-Type Presentation Tests ===");

// -------------------------------------------------------------
// Test A — GlowBook App Launch
// -------------------------------------------------------------
console.log("\n--- Sentinel Test A: GlowBook App Launch ---");
const glowBookChecklist: IntakeChecklistState = {
  campaign_type: "app_launch",
  campaign_name: "GlowBook",
  objective: "Drive mobile app downloads",
  cta_url: "https://glowbook.app/download",
};
const glowBookPlan: CampaignPlanDocument = {
  title: "GlowBook Launch Plan",
  executive_summary: "AI-driven mobile journaling app launch",
  core_strategy: {
    objective: "Drive mobile app downloads",
    messaging_pillars: ["Smart Journaling", "Privacy First", "Habit Builder"],
  },
};

const stratA = transformPlanToStrategyView(glowBookPlan, glowBookChecklist);
assert.equal(stratA.campaignName, "GlowBook", "GlowBook title displayed as canonical campaignName");
assert.equal(stratA.eventName, "GlowBook", "GlowBook title mapped to eventName for backwards compatibility");
assert.equal(stratA.campaignType, "app_launch", "app-launch context preserved");
assert.equal(stratA.ctaUrl, "https://glowbook.app/download", "CTA URL preserved");
assert.equal(stratA.ctaLabel, "Download / CTA Link:", "CTA label is download-oriented");
assert.equal(stratA.venue, undefined, "NO Venue on app_launch");
assert.equal(stratA.ticketPrice, undefined, "NO Admission on app_launch");
assert.equal(stratA.capacity, undefined, "NO Seats on app_launch");
assert.equal(stratA.curriculum, undefined, "NO Curriculum on app_launch");
assert.equal(stratA.guestSpeaker, undefined, "NO invented guest on app_launch");
assert.equal(stratA.date, undefined, "Launch date undefined when not supplied");
console.log("✓ Sentinel Test A passed!");

// -------------------------------------------------------------
// Test B — Hospital Physical Launch Event
// -------------------------------------------------------------
console.log("\n--- Sentinel Test B: NovaCare Hospital Launch Event ---");
const hospitalChecklist: IntakeChecklistState = {
  campaign_type: "physical_event",
  campaign_name: "NovaCare Hospital Launch",
  venue: "Grand Hall, City Medical Center",
  event_date: "November 12, 2026 • 10:00 AM",
  has_guest: true,
  guest_name: "Dr. Ayesha Malik",
  guest_title: "Chief of Surgery",
};
const hospitalPlan: CampaignPlanDocument = {
  title: "NovaCare Plan",
  executive_summary: "Opening ceremony and community health day",
  core_strategy: {
    objective: "Engage local medical community",
    messaging_pillars: ["World-class care", "Advanced diagnostics"],
  },
};

const stratB = transformPlanToStrategyView(hospitalPlan, hospitalChecklist);
assert.equal(stratB.campaignName, "NovaCare Hospital Launch", "Physical event title displayed");
assert.equal(stratB.venue, "Grand Hall, City Medical Center", "Venue displayed when supplied");
assert.equal(stratB.date, "November 12, 2026 • 10:00 AM", "Event date displayed when supplied");
assert.equal(stratB.dateLabel, "Event Date", "Date label appropriate for physical event");
assert.equal(stratB.guestSpeaker, "Dr. Ayesha Malik (Chief of Surgery)", "Actual guest displayed with title");
assert.equal(stratB.curriculum, undefined, "Curriculum is absent when not supplied (not invented)");
assert.equal(stratB.ticketPrice, undefined, "Admission is absent when not supplied (not invented)");
assert.equal(stratB.capacity, undefined, "Seats are absent when not supplied (not invented)");
console.log("✓ Sentinel Test B passed!");

// -------------------------------------------------------------
// Test C — Webinar
// -------------------------------------------------------------
console.log("\n--- Sentinel Test C: Webinar ---");
const webinarChecklist: IntakeChecklistState = {
  campaign_type: "webinar",
  event_name: "Mastering Agentic AI Architectures",
  event_date: "December 5, 2026 • 4:00 PM UTC",
  registration_link: "https://webinar.ai/register",
  has_guest: false,
};
const webinarPlan: CampaignPlanDocument = {
  title: "Webinar Plan",
  executive_summary: "Online live masterclass",
  core_strategy: {
    objective: "Developer education and lead generation",
    messaging_pillars: ["Agent design patterns", "Production observability"],
  },
};

const stratC = transformPlanToStrategyView(webinarPlan, webinarChecklist);
assert.equal(stratC.campaignName, "Mastering Agentic AI Architectures", "Webinar title displayed");
assert.equal(stratC.date, "December 5, 2026 • 4:00 PM UTC", "Webinar date displayed");
assert.equal(stratC.dateLabel, "Webinar Date", "Webinar date label used");
assert.equal(stratC.venue, undefined, "Physical venue not forced on webinar");
assert.equal(stratC.guestSpeaker, undefined, "No guest invented when has_guest is false");
assert.equal(stratC.ctaUrl, "https://webinar.ai/register", "Registration link preserved");
assert.equal(stratC.ctaLabel, "Registration Portal:", "Webinar portal label used");
console.log("✓ Sentinel Test C passed!");

// -------------------------------------------------------------
// Test D — Missing Optional Fields / General Promotion
// -------------------------------------------------------------
console.log("\n--- Sentinel Test D: Missing Optional Fields & General Promotion ---");
const promoChecklist: IntakeChecklistState = {
  campaign_type: "general_promotion",
  campaign_name: "Spring AI Boost 2026",
  objective: "Brand awareness",
};
const promoPlan: CampaignPlanDocument = {
  title: "Spring Promo Plan",
  executive_summary: "Multi-channel promotion",
  core_strategy: {
    objective: "Brand awareness",
    messaging_pillars: ["Spring savings", "AI efficiency"],
  },
};

const stratD = transformPlanToStrategyView(promoPlan, promoChecklist);
assert.equal(stratD.campaignName, "Spring AI Boost 2026", "General promotion title displayed");
assert.equal(stratD.venue, undefined, "Venue undefined for general promotion");
assert.equal(stratD.ticketPrice, undefined, "Ticket price undefined");
assert.equal(stratD.capacity, undefined, "Capacity undefined");
assert.equal(stratD.guestSpeaker, undefined, "Guest speaker undefined");
assert.equal(stratD.curriculum, undefined, "Curriculum undefined");
assert.equal(stratD.date, undefined, "Date undefined when not supplied");
console.log("✓ Sentinel Test D passed!");

// -------------------------------------------------------------
// Test E — Solo Host (No Guest) eradicated from codebase
// -------------------------------------------------------------
console.log("\n--- Sentinel Test E: Verifying 'Solo Host (No Guest)' Eradication ---");
const artifactPanelContent = fs.readFileSync(
  path.resolve("src/components/campaign/ArtifactPanel.tsx"),
  "utf8"
);
assert.ok(
  !artifactPanelContent.includes("Solo Host (No Guest)"),
  "ArtifactPanel.tsx must NOT contain 'Solo Host (No Guest)'"
);
assert.ok(
  !artifactPanelContent.includes("Solo Host"),
  "ArtifactPanel.tsx must NOT contain 'Solo Host'"
);

const apiAdapterContent = fs.readFileSync(
  path.resolve("src/components/campaign/apiAdapter.ts"),
  "utf8"
);
assert.ok(
  !apiAdapterContent.includes("Solo Host (No Guest)"),
  "apiAdapter.ts must NOT contain 'Solo Host (No Guest)'"
);
console.log("✓ Sentinel Test E passed!");

// -------------------------------------------------------------
// Test F — Research Status Display Preserved
// -------------------------------------------------------------
console.log("\n--- Sentinel Test F: Research Status Preserved ---");
assert.ok(
  artifactPanelContent.includes('strategy.researchStatus === "degraded"'),
  "degraded research status alert preserved"
);
assert.ok(
  artifactPanelContent.includes('strategy.researchStatus === "no_evidence"'),
  "no_evidence research status alert preserved"
);
console.log("✓ Sentinel Test F passed!");

console.log("\nALL SENTINEL TESTS PASSED SUCCESSFULLY!");


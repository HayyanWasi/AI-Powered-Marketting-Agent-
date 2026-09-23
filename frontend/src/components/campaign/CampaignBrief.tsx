"use client";

import type { IntakeChecklistState, CampaignPlanDocument } from "@/lib/api";

interface Props {
  checklist: IntakeChecklistState | null;
  plan: CampaignPlanDocument | null;
  generated: boolean;
}

/** Derive a human duration from the plan's schedule window, if present. */
function deriveDuration(plan: CampaignPlanDocument | null): string {
  const start = plan?.schedule_plan?.campaign_start;
  const end = plan?.schedule_plan?.campaign_end;
  if (start && end) {
    const days = Math.round(
      (Date.parse(end) - Date.parse(start)) / (1000 * 60 * 60 * 24)
    );
    if (Number.isFinite(days) && days > 0) return `${days} days`;
  }
  return "";
}

export default function CampaignBrief({ checklist, plan, generated }: Props) {
  // Every value is sourced from real backend data only. Missing = "Not set yet".
  const fields: { label: string; value: string }[] = [
    { label: "Goal", value: (checklist?.objective ?? "").trim() },
    {
      label: "Audience",
      value: (
        checklist?.target_audience ||
        (typeof checklist?.audience_profile === "object" && checklist?.audience_profile !== null
          ? (checklist?.audience_profile as { summary?: string }).summary
          : (checklist?.audience_profile as string | undefined)) ||
        ""
      ).trim(),
    },
    { label: "Duration", value: deriveDuration(plan) },
    {
      label: "Frequency",
      value: (
        plan?.schedule_plan?.recommended_cadence ||
        plan?.channel_plan?.overall_cadence ||
        ""
      ).trim(),
    },
    {
      label: "Themes",
      value: (plan?.core_strategy?.messaging_pillars ?? []).join(", ").trim(),
    },
    { label: "Tone", value: (plan?.core_strategy?.tone_of_voice ?? "").trim() },
    {
      label: "CTA",
      value: (checklist?.cta_url || checklist?.registration_link || "").trim(),
    },
  ];

  const ready = fields.filter((f) => f.value).length;
  const total = fields.length;

  return (
    <aside className="hidden lg:flex w-[320px] shrink-0 flex-col border-l border-[#e6e9ec] bg-[#fbfcfc] h-full">
      <div className="px-5 pt-5 pb-3">
        <h2 className="text-[15px] font-semibold text-[#1f2a30]">Campaign brief</h2>
        <p className="text-[12px] text-[#8a949c] mt-0.5">
          {ready} of {total} details ready
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-5 pb-4 space-y-4">
        {fields.map((f) => (
          <div key={f.label}>
            <p className="text-[11px] font-semibold tracking-[0.04em] text-[#116677] uppercase mb-1">
              {f.label}
            </p>
            {f.value ? (
              <p className="text-[13.5px] leading-snug text-[#26333b]">{f.value}</p>
            ) : (
              <p className="text-[13px] italic text-[#aab2b8]">Not set yet</p>
            )}
          </div>
        ))}
      </div>

      {generated && (
        <div className="border-t border-[#eef0f2] p-4">
          <p className="text-[12.5px] text-[#3a8f6b] flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#3a8f6b]" />
            Campaign generated. Open the Content tab to review.
          </p>
        </div>
      )}
    </aside>
  );
}

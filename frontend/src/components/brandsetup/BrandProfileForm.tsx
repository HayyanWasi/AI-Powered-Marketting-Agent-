"use client";

import { BrandProfileData } from "./types";

interface Props {
  formData: BrandProfileData;
  setFormData: React.Dispatch<React.SetStateAction<BrandProfileData>>;
  onSave: () => void;
  isSaved: boolean;
  isSaving?: boolean;
}

export default function BrandProfileForm({
  formData,
  setFormData,
  onSave,
  isSaved,
  isSaving = false,
}: Props) {
  return (
    <div className="rounded-lg bg-[#111820] border border-[#25303B] divide-y divide-[#25303B] shadow-sm">
      {/* 1. Company Profile & Identity */}
      <section className="p-6 sm:p-8 space-y-5">
        <div>
          <h2 className="text-base font-semibold text-[#F3F4F6] tracking-tight">
            1. Company Profile & Identity
          </h2>
          <p className="text-xs text-[#9CA3AF] mt-0.5">
            Basic company details and primary market audience definition.
          </p>
        </div>

        <div className="space-y-4 pt-1">
          {/* Row 1: Company Name & Website URL in 2-column grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-[#D1D5DB] mb-1.5">
                Company Name <span className="text-[#3B82F6]">*</span>
              </label>
              <input
                type="text"
                value={formData.companyName}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, companyName: e.target.value }))
                }
                placeholder="e.g. Hipoclipse"
                className="w-full h-11 px-3.5 rounded-lg bg-[#0D141B] border border-[#25303B] text-sm text-[#F3F4F6] placeholder-[#6B7280] focus:outline-none focus:ring-1 focus:ring-[#3B82F6] focus:border-[#3B82F6] transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[#D1D5DB] mb-1.5">
                Website URL
              </label>
              <input
                type="url"
                value={formData.website}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, website: e.target.value }))
                }
                placeholder="https://hipoclipse.ai"
                className="w-full h-11 px-3.5 rounded-lg bg-[#0D141B] border border-[#25303B] text-sm text-[#F3F4F6] placeholder-[#6B7280] focus:outline-none focus:ring-1 focus:ring-[#3B82F6] focus:border-[#3B82F6] transition-colors"
              />
            </div>
          </div>

          {/* Row 2: Primary Target Audience */}
          <div>
            <label className="block text-xs font-medium text-[#D1D5DB] mb-1.5">
              Primary Target Audience
            </label>
            <input
              type="text"
              value={formData.targetAudience}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, targetAudience: e.target.value }))
              }
              placeholder="e.g. Enterprise CMOs, Retail Brands & B2B Distributors"
              className="w-full h-11 px-3.5 rounded-lg bg-[#0D141B] border border-[#25303B] text-sm text-[#F3F4F6] placeholder-[#6B7280] focus:outline-none focus:ring-1 focus:ring-[#3B82F6] focus:border-[#3B82F6] transition-colors"
            />
            <span className="text-[11px] text-[#6B7280] mt-1 block">
              Helps conversational models adapt language and industry context.
            </span>
          </div>
        </div>
      </section>

      {/* 2. What We Do & Proven Track Record */}
      <section className="p-6 sm:p-8 space-y-5">
        <div>
          <h2 className="text-base font-semibold text-[#F3F4F6] tracking-tight">
            2. What We Do & Proven Track Record
          </h2>
          <p className="text-xs text-[#9CA3AF] mt-0.5">
            Core mission and verifiable milestones used by AI to back up conversational claims.
          </p>
        </div>

        <div className="space-y-4 pt-1">
          {/* Core Mission */}
          <div>
            <label className="block text-xs font-medium text-[#D1D5DB] mb-1.5">
              What does your company do? (Core Mission) <span className="text-[#3B82F6]">*</span>
            </label>
            <textarea
              rows={3}
              value={formData.description}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, description: e.target.value }))
              }
              placeholder="Describe your company's core value proposition, solutions, and services..."
              className="w-full p-4 rounded-lg bg-[#0D141B] border border-[#25303B] text-sm text-[#F3F4F6] placeholder-[#6B7280] focus:outline-none focus:ring-1 focus:ring-[#3B82F6] focus:border-[#3B82F6] transition-colors leading-relaxed resize-y"
            />
          </div>

          {/* Track Record */}
          <div>
            <label className="block text-xs font-medium text-[#D1D5DB] mb-1.5">
              What have you done? (Track Record & Key Achievements) <span className="text-[#3B82F6]">*</span>
            </label>
            <textarea
              rows={3}
              value={formData.trackRecord}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, trackRecord: e.target.value }))
              }
              placeholder="e.g. Over $4B automated in sales, 1M+ retail stores digitized for brands like Coca-Cola FEMSA and Nestlé..."
              className="w-full p-4 rounded-lg bg-[#0D141B] border border-[#25303B] text-sm text-[#F3F4F6] placeholder-[#6B7280] focus:outline-none focus:ring-1 focus:ring-[#3B82F6] focus:border-[#3B82F6] transition-colors leading-relaxed resize-y"
            />
          </div>
        </div>
      </section>

      {/* 3. Brand Tone & Voice Signature */}
      <section className="p-6 sm:p-8 space-y-5">
        <div>
          <h2 className="text-base font-semibold text-[#F3F4F6] tracking-tight">
            3. Brand Tone & Voice Signature
          </h2>
          <p className="text-xs text-[#9CA3AF] mt-0.5">
            Natural language communication style instructions enforced during agent interactions.
          </p>
        </div>

        <div className="space-y-2 pt-1">
          <label className="block text-xs font-medium text-[#D1D5DB] mb-1.5">
            Brand Voice & Communication Style Message <span className="text-[#3B82F6]">*</span>
          </label>
          <div className="rounded-lg bg-[#0D141B] border border-[#25303B] focus-within:ring-1 focus-within:ring-[#3B82F6] focus-within:border-[#3B82F6] transition-colors">
            <textarea
              rows={5}
              value={formData.toneMessage}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, toneMessage: e.target.value }))
              }
              placeholder="Tell the AI how your brand communicates. E.g.: 'We sound like an experienced, supportive enterprise partner who is friendly, direct, and pragmatic. We avoid high-pressure sales talk, speak in clear plain language, and always prioritize genuine customer value over marketing fluff...'"
              className="w-full p-4 bg-transparent text-sm text-[#F3F4F6] placeholder-[#6B7280] focus:outline-none leading-relaxed resize-y"
            />

            {/* Bottom helper & counter bar */}
            <div className="flex items-center justify-between px-4 py-2.5 border-t border-[#25303B]/60 text-xs text-[#6B7280]">
              <span>Used by AI models during content and agent generations</span>
              <span className="font-mono text-[11px]">{formData.toneMessage.length} characters</span>
            </div>
          </div>
        </div>
      </section>

      {/* Save Confirmation Notification Banner */}
      {isSaved && (
        <div className="px-6 py-3.5 bg-emerald-500/10 border-t border-emerald-500/20 text-emerald-400 text-xs sm:text-sm font-medium flex items-center justify-between">
          <span>Brand Setup saved successfully.</span>
        </div>
      )}

      {/* Form Action Footer: Aligned to Bottom-Right */}
      <div className="p-4 sm:p-6 bg-[#0D141B]/40 flex items-center justify-end space-x-3">
        <button
          type="button"
          onClick={() => {
            // Optional reset or cancel action
          }}
          className="px-4 py-2 rounded-lg border border-[#25303B] bg-transparent hover:bg-[#171D25] text-xs sm:text-sm text-[#9CA3AF] hover:text-[#F3F4F6] font-medium transition-colors cursor-pointer"
        >
          Cancel
        </button>

        <button
          type="button"
          onClick={onSave}
          disabled={isSaving}
          className="px-5 py-2 rounded-lg bg-[#3B82F6] hover:bg-[#2563EB] text-white text-xs sm:text-sm font-medium transition-colors shadow-sm cursor-pointer"
        >
          {isSaving ? "Saving..." : "Save changes"}
        </button>
      </div>
    </div>
  );
}

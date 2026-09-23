"use client";

import { useState } from "react";
import {
  X,
  Layers,
  Sparkles,
  Target,
  Calendar,
  MapPin,
  Users,
  Award,
  Link2,
  BookOpen,
  TrendingUp,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { ClimbingBoxLoader } from "react-spinners";
import { LinkedInArtifact } from "./types";
import LinkedInPostCard from "./LinkedInPostCard";
import LinkedInLaunchControl from "@/components/linkedin/LinkedInLaunchControl";

interface Props {
  artifact: LinkedInArtifact | null;
  isOpen: boolean;
  onClose: () => void;
  isGenerating?: boolean;
}

export default function ArtifactPanel({
  artifact,
  isOpen,
  onClose,
  isGenerating = false,
}: Props) {
  // Main view: 'strategy' or 'posts'
  const [mainTab, setMainTab] = useState<"strategy" | "posts">("strategy");
  const [selectedPostTab, setSelectedPostTab] = useState<number | "all">(0);

  if (!isOpen || !artifact) return null;

  const strategy = artifact.strategy;

  return (
    <div className="w-full md:w-[480px] lg:w-[560px] xl:w-[620px] h-full flex flex-col bg-[#0E141B] border-l border-white/[0.08] shadow-2xl relative z-20 transition-all duration-200 select-text font-sans">
      {/* Top Header Bar */}
      <div className="px-5 py-3.5 border-b border-white/[0.08] bg-[#151D26] flex items-center justify-between flex-shrink-0">
        <div className="flex items-center space-x-2.5">
          <div className="w-7 h-7 rounded-md bg-[#00c2ee]/10 border border-[#00c2ee]/20 text-[#00c2ee] flex items-center justify-center">
            <Layers size={15} />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-xs sm:text-sm font-semibold text-[#F5F7FA] tracking-tight">
                {strategy?.campaignName || strategy?.eventName || artifact.title || "Campaign Studio"}
              </h2>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#00c2ee]/10 text-[#00c2ee] font-medium border border-[#00c2ee]/20">
                AI Generated
              </span>
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={onClose}
          aria-label="Close studio panel"
          className="p-1.5 rounded-md text-[#6B7785] hover:text-[#F5F7FA] hover:bg-white/[0.04] transition-colors cursor-pointer"
        >
          <X size={15} />
        </button>
      </div>

      {/* Primary Section Switcher: Strategy Blueprint vs LinkedIn Posts */}
      <div className="px-4 py-2 border-b border-white/[0.08] bg-[#121820] flex items-center space-x-2">
        <button
          type="button"
          onClick={() => setMainTab("strategy")}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all cursor-pointer ${mainTab === "strategy"
            ? "bg-[#00c2ee]/15 text-[#00c2ee] border border-[#00c2ee]/30 shadow-sm"
            : "text-[#9AA6B2] hover:text-white hover:bg-white/[0.03] border border-transparent"
            }`}
        >
          <Target size={13} />
          <span>Strategy Blueprint</span>
        </button>

        <button
          type="button"
          onClick={() => setMainTab("posts")}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all cursor-pointer ${mainTab === "posts"
            ? "bg-[#d75dff]/15 text-[#d75dff] border border-[#d75dff]/30 shadow-sm"
            : "text-[#9AA6B2] hover:text-white hover:bg-white/[0.03] border border-transparent"
            }`}
        >
          <Sparkles size={13} className={isGenerating && artifact.posts.length === 0 ? "animate-spin text-[#d75dff]" : ""} />
          <span>
            LinkedIn Posts {artifact.posts.length > 0 ? `(${artifact.posts.length})` : isGenerating ? "(Generating...)" : "(0)"}
          </span>
        </button>
      </div>

      {/* ── TAB 1: STRATEGY BLUEPRINT VIEW ────────────────────────────────────── */}
      {mainTab === "strategy" && (
        <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
          {strategy ? (
            (() => {
              const rawType = (strategy.campaignType || "").toLowerCase().trim();
              const isLaunch = ["app_launch", "product_launch", "service_launch"].includes(rawType);
              const isPhysicalEvent = rawType === "physical_event";
              const isWebinar = rawType === "webinar";
              const isGeneralPromo = rawType === "general_promotion";

              let badgeText = "Strategic Blueprint Overview";
              if (rawType === "app_launch") badgeText = "App Launch Strategy";
              else if (rawType === "product_launch") badgeText = "Product Launch Strategy";
              else if (rawType === "service_launch") badgeText = "Service Launch Strategy";
              else if (rawType === "physical_event") badgeText = "Event Strategy Blueprint";
              else if (rawType === "webinar") badgeText = "Webinar Strategy Blueprint";
              else if (rawType === "general_promotion") badgeText = "Campaign Promotion Blueprint";

              const displayName =
                strategy.campaignName ||
                strategy.eventName ||
                artifact.title ||
                "Campaign Strategy";

              // Build parameter cards that are actually applicable and supplied
              const paramCards: Array<{
                id: string;
                icon: React.ReactNode;
                label: string;
                value: string;
              }> = [];

              // Date: shown only if genuinely supplied, with campaign-appropriate label
              const displayDate = (strategy.date || strategy.eventDate || "").trim();
              if (displayDate) {
                const dateLabel =
                  strategy.dateLabel ||
                  (isLaunch
                    ? "Launch Date"
                    : isWebinar
                      ? "Webinar Date"
                      : isPhysicalEvent
                        ? "Event Date"
                        : "Date");
                paramCards.push({
                  id: "date",
                  icon: <Calendar size={12} className="text-[#00c2ee]" />,
                  label: dateLabel,
                  value: displayDate,
                });
              }

              // Venue: ONLY for physical events (or unspecified event types), ONLY if genuinely supplied
              if (!isLaunch && !isGeneralPromo && !isWebinar && strategy.venue && strategy.venue.trim()) {
                paramCards.push({
                  id: "venue",
                  icon: <MapPin size={12} className="text-[#00c2ee]" />,
                  label: "Venue",
                  value: strategy.venue.trim(),
                });
              }

              // Keynote / Guest Speaker: ONLY for physical events or webinars, ONLY if genuinely supplied
              if (!isLaunch && !isGeneralPromo && strategy.guestSpeaker && strategy.guestSpeaker.trim()) {
                paramCards.push({
                  id: "guest",
                  icon: <Award size={12} className="text-[#d75dff]" />,
                  label: "Keynote Speaker",
                  value: strategy.guestSpeaker.trim(),
                });
              }

              // Admission & Seats: ONLY for physical events or webinars, ONLY if genuinely supplied
              if (!isLaunch && !isGeneralPromo) {
                const hasPrice = Boolean(strategy.ticketPrice && strategy.ticketPrice.trim());
                const hasCapacity = Boolean(strategy.capacity && strategy.capacity.trim());
                if (hasPrice || hasCapacity) {
                  const admissionValue =
                    hasPrice && hasCapacity
                      ? `${strategy.ticketPrice} • ${strategy.capacity}`
                      : strategy.ticketPrice || strategy.capacity || "";
                  paramCards.push({
                    id: "admission",
                    icon: <Users size={12} className="text-[#10b981]" />,
                    label: hasCapacity ? "Admission & Seats" : "Admission",
                    value: admissionValue,
                  });
                }
              }

              // Category (if supplied)
              if (strategy.category && strategy.category.trim()) {
                paramCards.push({
                  id: "category",
                  icon: <Layers size={12} className="text-[#00c2ee]" />,
                  label: "Category",
                  value: strategy.category.trim(),
                });
              }

              // Campaign Objective (if supplied and launch/promo)
              if ((isLaunch || isGeneralPromo) && strategy.objective && strategy.objective.trim()) {
                paramCards.push({
                  id: "objective",
                  icon: <Target size={12} className="text-[#10b981]" />,
                  label: "Campaign Objective",
                  value: strategy.objective.trim(),
                });
              }

              // Target audience, curriculum & CTA
              const showCurriculum =
                !isLaunch &&
                !isGeneralPromo &&
                Boolean(strategy.curriculum && strategy.curriculum.trim());

              const ctaLink = (strategy.ctaUrl || strategy.registrationLink || "").trim();
              const ctaLabel =
                strategy.ctaLabel ||
                (isLaunch
                  ? "Download / CTA Link:"
                  : isPhysicalEvent || isWebinar
                    ? "Registration Portal:"
                    : "Campaign Link:");

              const hasTargetAudience = Boolean(
                strategy.targetAudience && strategy.targetAudience.trim()
              );

              return (
                <>
                  {/* Non-blocking Research Status Notice */}
                  {strategy.researchStatus === "degraded" && (
                    <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-start space-x-2.5 shadow-sm">
                      <AlertTriangle size={15} className="mt-0.5 shrink-0 text-amber-400" />
                      <span className="leading-relaxed">
                        Strategy generated, but live research was unavailable. Some recommendations are based on campaign and brand context rather than current external research.
                      </span>
                    </div>
                  )}
                  {strategy.researchStatus === "no_evidence" && (
                    <div className="p-3 rounded-xl bg-sky-500/10 border border-sky-500/20 text-sky-300 text-xs flex items-start space-x-2.5 shadow-sm">
                      <AlertTriangle size={15} className="mt-0.5 shrink-0 text-sky-400" />
                      <span className="leading-relaxed">
                        Strategy generated, but live research returned no usable external evidence. Recommendations are based on campaign and brand context.
                      </span>
                    </div>
                  )}

                  {/* Executive Summary Card */}
                  <div className="p-4 rounded-xl bg-gradient-to-br from-[#151D26] to-[#0E151C] border border-[#272F38] shadow-md">
                    <div className="flex items-center space-x-2 mb-2">
                      <span className="w-2 h-2 rounded-full bg-[#00c2ee] animate-pulse" />
                      <span className="text-[11px] font-bold uppercase tracking-wider text-[#00c2ee]">
                        {badgeText}
                      </span>
                    </div>
                    <h3 className="text-sm font-semibold text-[#F5F7FA] mb-1.5">
                      {displayName}
                    </h3>
                    {strategy.executiveSummary && (
                      <p className="text-xs text-[#9AA6B2] leading-relaxed">
                        {strategy.executiveSummary}
                      </p>
                    )}
                  </div>

                  {/* Logistics & Parameters Grid (only renders when there are applicable supplied cards) */}
                  {paramCards.length > 0 && (
                    <div className="grid grid-cols-2 gap-2.5">
                      {paramCards.map((card) => (
                        <div
                          key={card.id}
                          className="p-3 rounded-lg bg-[#151D26]/70 border border-white/[0.06]"
                        >
                          <div className="flex items-center space-x-1.5 text-[#6B7785] text-[11px] mb-1">
                            {card.icon}
                            <span>{card.label}</span>
                          </div>
                          <div
                            className="text-xs font-medium text-[#F5F7FA] truncate"
                            title={card.value}
                          >
                            {card.value}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Target Demographic, Curriculum & CTA Link */}
                  {(hasTargetAudience || showCurriculum || ctaLink) && (
                    <div className="p-3.5 rounded-xl bg-[#151D26]/70 border border-white/[0.06] space-y-2.5">
                      {hasTargetAudience && (
                        <div>
                          <div className="flex items-center space-x-1.5 text-[#6B7785] text-[11px] mb-1">
                            <Target size={12} className="text-[#00c2ee]" />
                            <span>Target Demographic</span>
                          </div>
                          <p className="text-xs text-[#E1E7EC] font-medium">
                            {strategy.targetAudience}
                          </p>
                        </div>
                      )}

                      {showCurriculum && (
                        <div className={hasTargetAudience ? "pt-2 border-t border-white/[0.06]" : ""}>
                          <div className="flex items-center space-x-1.5 text-[#6B7785] text-[11px] mb-1">
                            <BookOpen size={12} className="text-[#d75dff]" />
                            <span>Core Curriculum & Deliverables</span>
                          </div>
                          <p className="text-xs text-[#9AA6B2] leading-relaxed">
                            {strategy.curriculum}
                          </p>
                        </div>
                      )}

                      {ctaLink && (
                        <div
                          className={
                            hasTargetAudience || showCurriculum
                              ? "pt-2 border-t border-white/[0.06] flex items-center justify-between text-xs"
                              : "flex items-center justify-between text-xs"
                          }
                        >
                          <span className="text-[#6B7785] flex items-center space-x-1">
                            <Link2 size={12} />
                            <span>{ctaLabel}</span>
                          </span>
                          <a
                            href={ctaLink}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[#00c2ee] hover:underline font-mono truncate max-w-[200px]"
                          >
                            {ctaLink}
                          </a>
                        </div>
                      )}
                    </div>
                  )}

                  {/* 3 Core Messaging Pillars */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-[#F5F7FA] flex items-center space-x-1.5">
                        <Sparkles size={13} className="text-[#00c2ee]" />
                        <span>3 Core Messaging Pillars</span>
                      </span>
                      <span className="text-[11px] text-[#6B7785]">Angle Architecture</span>
                    </div>

                    {strategy.pillars.map((pillar, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-lg bg-[#121922] border border-white/[0.05] hover:border-[#00c2ee]/30 transition-all"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-[11px] font-bold text-[#00c2ee]">
                            Pillar 0{idx + 1} • {pillar.title}
                          </span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/[0.05] text-[#9AA6B2]">
                            {pillar.angle}
                          </span>
                        </div>
                        <p className="text-xs text-[#D1D9E0] italic">
                          &ldquo;{pillar.hook}&rdquo;
                        </p>
                      </div>
                    ))}
                  </div>

                  {/* Distribution Cadence & KPIs */}
                  <div className="p-3.5 rounded-xl bg-[#151D26]/70 border border-white/[0.06]">
                    <div className="flex items-center space-x-1.5 text-[#10b981] text-xs font-semibold mb-2">
                      <TrendingUp size={13} />
                      <span>Target KPIs & Growth Goals</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      {strategy.kpis.map((kpi, idx) => (
                        <div key={idx} className="flex items-center space-x-1.5 text-[#9AA6B2]">
                          <CheckCircle2 size={12} className="text-[#10b981] flex-shrink-0" />
                          <span className="truncate">{kpi}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Transition to Content Button */}
                  <button
                    type="button"
                    onClick={() => setMainTab("posts")}
                    className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-[#00c2ee] to-[#d75dff] hover:opacity-95 text-black text-xs font-bold flex items-center justify-center space-x-2 shadow-lg cursor-pointer transition-all"
                  >
                    <span>View Generated LinkedIn Posts ({artifact.posts.length})</span>
                    <ArrowRight size={14} />
                  </button>
                </>
              );
            })()
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center py-16 text-center space-y-6">
              <div className="py-4">
                <ClimbingBoxLoader color="#00c2ee" size={15} />
              </div>
              <div className="space-y-1.5 max-w-xs">
                <h4 className="text-sm font-semibold text-[#F5F7FA]">
                  Synthesizing Strategy Blueprint...
                </h4>
                <p className="text-xs text-[#9AA6B2] leading-relaxed">
                  This may take some time. Building messaging pillars and audience target frameworks.
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── TAB 2: LINKEDIN POSTS VIEW ────────────────────────────────────────── */}
      {mainTab === "posts" && (
        <>
          {/* Segmented Control / Clean Underline Navigation Tabs */}
          {artifact.posts.length > 1 && (
            <div className="px-5 border-b border-white/[0.08] bg-[#151D26]/50 flex items-center space-x-4 overflow-x-auto text-xs">
              <button
                type="button"
                onClick={() => setSelectedPostTab("all")}
                className={`py-2.5 font-medium border-b-2 transition-colors cursor-pointer whitespace-nowrap ${selectedPostTab === "all"
                  ? "border-[#00c2ee] text-[#F5F7FA]"
                  : "border-transparent text-[#9AA6B2] hover:text-[#F5F7FA]"
                  }`}
              >
                All Variations ({artifact.posts.length})
              </button>

              {artifact.posts.map((post, idx) => (
                <button
                  key={post.id}
                  type="button"
                  onClick={() => setSelectedPostTab(idx)}
                  className={`py-2.5 font-medium border-b-2 transition-colors cursor-pointer whitespace-nowrap ${selectedPostTab === idx
                    ? "border-[#00c2ee] text-[#F5F7FA]"
                    : "border-transparent text-[#9AA6B2] hover:text-[#F5F7FA]"
                    }`}
                >
                  Variation {idx + 1}
                </button>
              ))}
            </div>
          )}

          {/* Draft Editor / Post Cards Scrollable List OR ClimbingBoxLoader Loading State */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
            {artifact.posts.length === 0 ? (
              <div className="h-full min-h-[320px] flex flex-col items-center justify-center text-center space-y-6 select-none py-12">
                <div className="py-6 flex items-center justify-center">
                  <ClimbingBoxLoader color="#00c2ee" size={16} />
                </div>

                <div className="space-y-2 max-w-sm px-4">
                  <div className="flex items-center justify-center space-x-2">
                    <span className="w-2 h-2 rounded-full bg-[#00c2ee] animate-pulse" />
                    <h4 className="text-sm font-semibold text-[#F5F7FA]">
                      Generating LinkedIn Campaign Content...
                    </h4>
                  </div>
                  <p className="text-xs text-[#9AA6B2] leading-relaxed">
                    This may take some time. The AI is crafting personalized hooks, educational value breakdowns, and high-converting calls-to-action based on your strategy blueprint.
                  </p>
                </div>

                <div className="px-3.5 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.08] text-[11px] text-[#00c2ee] flex items-center space-x-2 animate-pulse">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#00c2ee]" />
                  <span>Synthesizing multi-angle variations with AI</span>
                </div>
              </div>
            ) : selectedPostTab === "all" ? (
              artifact.posts.map((post, idx) => (
                <LinkedInPostCard key={post.id} post={post} index={idx} />
              ))
            ) : (
              artifact.posts[selectedPostTab as number] && (
                <LinkedInPostCard
                  post={artifact.posts[selectedPostTab as number]}
                  index={selectedPostTab as number}
                />
              )
            )}
          </div>

          {/* Sticky Bottom Action: bind a verified LinkedIn account and launch. */}
          <div className="p-4 border-t border-white/[0.08] bg-[#151D26]">
            <LinkedInLaunchControl
              campaignId={artifact.campaignId}
              postCount={artifact.posts.length}
            />
          </div>
        </>
      )}
    </div>
  );
}

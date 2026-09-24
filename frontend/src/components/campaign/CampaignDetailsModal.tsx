"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  X,
  Calendar,
  Target,
  Users,
  Share2,
  ExternalLink,
  Copy,
  Check,
  FileText,
  Clock,
  CheckCircle2,
  AlertCircle,
  Layers,
  ArrowRight,
} from "lucide-react";
import { campaignApi, linkedinApi, Campaign } from "@/lib/api";

interface PostItem {
  id: string;
  campaign_id: string;
  slot_id?: string;
  hook?: string;
  body?: string;
  cta_text?: string;
  full_content?: string;
  status?: string;
  scheduled_at?: string;
  created_at?: string;
  media_url?: string;
  media_type?: string;
}

interface Props {
  campaignId: string | null;
  isOpen: boolean;
  onClose: () => void;
  initialCampaignName?: string;
}

function toLocalDateTimeValue(value?: string): string {
  if (!value) return "";
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

export default function CampaignDetailsModal({
  campaignId,
  isOpen,
  onClose,
  initialCampaignName,
}: Props) {
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [posts, setPosts] = useState<PostItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedPostId, setCopiedPostId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState(false);
  const [savingPostId, setSavingPostId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "content" | "schedule">("overview");

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const [retry, setRetry] = useState(0);

  // Fetch campaign details and posts
  useEffect(() => {
    if (!isOpen || !campaignId) {
      setCampaign(null);
      setPosts([]);
      setError(null);
      return;
    }

    let isMounted = true;
    setCampaign(null);
    setPosts([]);
    setLoading(true);
    setError(null);

    async function fetchData() {
      try {
        // Attempt fetching real campaign
        const [campRes, postsRes] = await Promise.all([
          campaignApi.get(campaignId!),
          campaignApi.getPosts(campaignId!),
        ]);

        if (!isMounted) return;

        setCampaign(campRes);
        setPosts(postsRes || []);
      } catch (err: unknown) {
        if (!isMounted) return;
        const msg = err instanceof Error ? err.message : "Failed to load campaign details";
        setError(msg);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    fetchData();

    return () => {
      isMounted = false;
    };
  }, [isOpen, campaignId, retry]);

  if (!isOpen) return null;

  const copyToClipboard = (text: string, idKey: string) => {
    navigator.clipboard.writeText(text);
    setCopiedPostId(idKey);
    setTimeout(() => setCopiedPostId(null), 2000);
  };

  const copyCampaignId = () => {
    if (!campaign?.id) return;
    navigator.clipboard.writeText(campaign.id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const getStateBadge = (state?: string) => {
    const s = (state || "Draft").toUpperCase();
    if (s.includes("ACTIVE") || s.includes("RUNNING") || s.includes("LAUNCHED")) {
      return (
        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse mr-1.5" />
          ACTIVE
        </span>
      );
    }
    if (s.includes("SCHEDULED")) {
      return (
        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <Clock size={12} className="mr-1.5" />
          SCHEDULED
        </span>
      );
    }
    if (s.includes("COMPLETED")) {
      return (
        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-zinc-800 text-zinc-300 border border-zinc-700">
          <CheckCircle2 size={12} className="mr-1.5 text-zinc-400" />
          COMPLETED
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
        <Clock size={12} className="mr-1.5" />
        {state || "Draft"}
      </span>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/70 backdrop-blur-md animate-in fade-in duration-200">
      {/* Modal Card */}
      <div
        className="relative w-full max-w-3xl max-h-[90vh] bg-[#11161D] border border-[#252C35] rounded-2xl shadow-2xl flex flex-col overflow-hidden text-zinc-100"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-zinc-800/80 bg-zinc-900/40">
          <div className="flex items-center space-x-3 min-w-0 pr-4">
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center flex-shrink-0">
              <Layers size={20} className="text-blue-400" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center space-x-2">
                <h2 className="text-base sm:text-lg font-bold text-zinc-100 truncate">
                  {campaign?.name || initialCampaignName || "Campaign Details"}
                </h2>
                {campaign && getStateBadge(campaign.state)}
              </div>
              <div className="flex items-center space-x-2 mt-0.5">
                <span className="text-[11px] font-mono text-zinc-400">
                  ID: {campaignId?.slice(0, 18)}...
                </span>
                <button
                  type="button"
                  onClick={copyCampaignId}
                  className="text-zinc-500 hover:text-zinc-300 p-0.5 rounded transition-colors"
                  title="Copy Campaign ID"
                >
                  {copiedId ? (
                    <Check size={12} className="text-emerald-400" />
                  ) : (
                    <Copy size={12} />
                  )}
                </button>
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-zinc-800/60 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 flex items-center justify-center transition-colors cursor-pointer flex-shrink-0"
            aria-label="Close modal"
          >
            <X size={16} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center space-x-1 px-5 pt-3 border-b border-zinc-800 bg-zinc-950/40">
          <button
            type="button"
            onClick={() => setActiveTab("overview")}
            className={`px-3.5 py-2 text-xs font-semibold rounded-t-lg transition-colors cursor-pointer border-b-2 ${
              activeTab === "overview"
                ? "border-blue-500 text-blue-400 bg-zinc-900/60"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Strategy & Audience
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("content")}
            className={`px-3.5 py-2 text-xs font-semibold rounded-t-lg transition-colors cursor-pointer border-b-2 flex items-center space-x-1.5 ${
              activeTab === "content"
                ? "border-blue-500 text-blue-400 bg-zinc-900/60"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <span>Generated Posts & Copy</span>
            {posts.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-blue-500/20 text-blue-300 font-mono">
                {posts.length}
              </span>
            )}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("schedule")}
            className={`px-3.5 py-2 text-xs font-semibold rounded-t-lg transition-colors cursor-pointer border-b-2 ${
              activeTab === "schedule"
                ? "border-blue-500 text-blue-400 bg-zinc-900/60"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Dispatch Schedule
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-6">
          {loading ? (
            <div className="py-16 flex flex-col items-center justify-center space-y-3">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-xs text-zinc-400">Loading campaign blueprint and assets...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start space-x-3 text-red-400 text-xs">
              <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold block">Failed to load details</span>
                <span className="text-zinc-400 mt-0.5 block">{error}<button onClick={() => setRetry((v) => v + 1)} className="ml-3 underline">Retry</button></span>
              </div>
            </div>
          ) : campaign ? (
            <>
              {/* Tab 1: Overview */}
              {activeTab === "overview" && (
                <div className="space-y-5">
                  {/* Primary Goal Card */}
                  <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800 space-y-2">
                    <div className="flex items-center space-x-2 text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                      <Target size={14} className="text-blue-400" />
                      <span>Primary Objective & Goal</span>
                    </div>
                    <p className="text-sm font-medium text-zinc-100">
                      {(campaign.goals as Record<string, any>)?.primary || campaign.name}
                    </p>
                    {Array.isArray((campaign.goals as Record<string, any>)?.metrics) &&
                      (campaign.goals as Record<string, any>).metrics.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {(campaign.goals as Record<string, any>).metrics.map(
                            (m: string, i: number) => (
                              <span
                                key={i}
                                className="px-2 py-0.5 rounded text-[11px] bg-zinc-800 text-zinc-300 border border-zinc-700 font-mono"
                              >
                                {m}
                              </span>
                            )
                          )}
                        </div>
                      )}
                  </div>

                  {/* Target Audience Card */}
                  <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800 space-y-3">
                    <div className="flex items-center space-x-2 text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                      <Users size={14} className="text-emerald-400" />
                      <span>Target Audience & ICP Segments</span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <span className="text-[11px] text-zinc-400 block mb-1">Target Segments:</span>
                        <div className="flex flex-wrap gap-1.5">
                          {((campaign.target_audience as Record<string, any>)?.segments || [
                            "General B2B Audience",
                          ]).map((seg: string, i: number) => (
                            <span
                              key={i}
                              className="px-2.5 py-0.5 rounded-full text-xs bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                            >
                              {seg}
                            </span>
                          ))}
                        </div>
                      </div>

                      {((campaign.target_audience as Record<string, any>)?.interests?.length > 0 ||
                        (campaign.target_audience as Record<string, any>)?.demographics) && (
                        <div>
                          <span className="text-[11px] text-zinc-400 block mb-1">
                            Key Interests / Context:
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {((campaign.target_audience as Record<string, any>)?.interests || []).map(
                              (int: string, i: number) => (
                                <span
                                  key={i}
                                  className="px-2.5 py-0.5 rounded-full text-xs bg-purple-500/10 text-purple-300 border border-purple-500/20"
                                >
                                  {int}
                                </span>
                              )
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Target Platforms */}
                  <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800 space-y-2">
                    <div className="flex items-center space-x-2 text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                      <Share2 size={14} className="text-purple-400" />
                      <span>Active Channels & Distribution</span>
                    </div>
                    <div className="flex flex-wrap gap-2 pt-1">
                      {(campaign.platforms || ["linkedin"]).map((plat, i) => (
                        <span
                          key={i}
                          className="capitalize px-3 py-1 rounded-lg text-xs font-medium bg-zinc-800/80 text-zinc-200 border border-zinc-700 flex items-center space-x-1.5"
                        >
                          <span className="w-2 h-2 rounded-full bg-blue-400" />
                          <span>{plat}</span>
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Metadata & Links (if available) */}
                  {campaign.metadata && Object.keys(campaign.metadata).length > 0 && (
                    <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800 space-y-2">
                      <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider block">
                        Campaign Deliverables & Links
                      </span>
                      <div className="space-y-1.5 text-xs text-zinc-300">
                        {Boolean(campaign.metadata.registration_link) && (
                          <div className="flex items-center space-x-2">
                            <span className="text-zinc-400">Registration Link:</span>
                            <a
                              href={String(campaign.metadata.registration_link)}
                              target="_blank"
                              rel="noreferrer"
                              className="text-blue-400 hover:underline flex items-center space-x-1 truncate max-w-sm"
                            >
                              <span>{String(campaign.metadata.registration_link)}</span>
                              <ExternalLink size={11} />
                            </a>
                          </div>
                        )}
                        {Boolean(campaign.metadata.outcome_deliverable) && (
                          <div>
                            <span className="text-zinc-400 block">Core Deliverable:</span>
                            <span className="text-zinc-200 mt-0.5 block">
                              {String(campaign.metadata.outcome_deliverable)}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 2: Content & Generated Posts */}
              {activeTab === "content" && (
                <div className="space-y-4">
                  <div className="flex justify-end">
                    <Link
                      href={`/video-generation?campaign=${campaign.id}`}
                      className="rounded-md border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-xs font-semibold text-blue-300 hover:bg-blue-500/20"
                    >
                      Generate campaign video
                    </Link>
                  </div>
                  {posts.length === 0 ? (
                    <div className="p-8 rounded-xl bg-zinc-950/60 border border-zinc-800 text-center space-y-3">
                      <FileText size={32} className="mx-auto text-zinc-600" />
                      <div>
                        <h4 className="text-sm font-semibold text-zinc-200">
                          No Generated Posts Yet
                        </h4>
                        <p className="text-xs text-zinc-400 mt-1 max-w-md mx-auto">
                          This campaign blueprint has been established. You can generate scheduled
                          LinkedIn posts and multi-day outreach sequences using the AI Launchpad.
                        </p>
                      </div>
                      <Link
                        href={`/new-campaign?campaign=${campaign.id}`}
                        className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition-all cursor-pointer shadow-lg shadow-blue-900/30"
                      >
                        <FileText size={14} />
                        <span>Generate Campaign Content</span>
                      </Link>
                    </div>
                  ) : (
                    posts.map((post, idx) => (
                      <div
                        key={post.id || idx}
                        className="p-4 rounded-xl bg-zinc-950/80 border border-zinc-800/90 space-y-3 relative group"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[11px] font-mono">
                              {post.slot_id || `Post #${idx + 1}`}
                            </span>
                            {post.scheduled_at && (
                              <span className="text-xs text-zinc-400 flex items-center space-x-1">
                                <Clock size={11} className="text-zinc-500" />
                                <span>{post.scheduled_at}</span>
                              </span>
                            )}
                          </div>

                          <div className="flex items-center space-x-2">
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              {(post.status || "Ready").toUpperCase()}
                            </span>
                            <button
                              type="button"
                              onClick={() =>
                                copyToClipboard(
                                  post.full_content || `${post.hook}\n\n${post.body}\n\n${post.cta_text}`,
                                  post.id
                                )
                              }
                              className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
                              title="Copy Post Content"
                            >
                              {copiedPostId === post.id ? (
                                <Check size={14} className="text-emerald-400" />
                              ) : (
                                <Copy size={14} />
                              )}
                            </button>
                          </div>
                        </div>

                        {/* Post Hook */}
                        {post.media_type === "video" && post.media_url && (
                          <video
                            src={post.media_url}
                            controls
                            preload="metadata"
                            className="max-h-[460px] w-full rounded-lg bg-black object-contain"
                          />
                        )}

                        {post.hook && (
                          <p className="text-xs font-semibold text-zinc-100 leading-snug">
                            &ldquo;{post.hook}&rdquo;
                          </p>
                        )}

                        {/* Post Body */}
                        {post.body && (
                          <div className="text-xs text-zinc-300 whitespace-pre-line leading-relaxed bg-zinc-900/50 p-3 rounded-lg border border-zinc-800/60 font-sans">
                            {post.body}
                          </div>
                        )}

                        {post.media_type === "video" && (
                          <div className="grid gap-3 rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                            <label className="grid gap-1 text-[11px] text-zinc-400">
                              Caption
                              <textarea
                                defaultValue={post.body || post.full_content || ""}
                                id={`caption-${post.id}`}
                                className="min-h-24 rounded-md border border-zinc-700 bg-zinc-900 p-2 text-xs text-zinc-100"
                              />
                            </label>
                            <label className="grid gap-1 text-[11px] text-zinc-400">
                              Publication date and time
                              <input
                                type="datetime-local"
                                id={`schedule-${post.id}`}
                                defaultValue={toLocalDateTimeValue(post.scheduled_at)}
                                className="rounded-md border border-zinc-700 bg-zinc-900 p-2 text-xs text-zinc-100"
                              />
                            </label>
                            <button
                              type="button"
                              disabled={savingPostId === post.id}
                              onClick={async () => {
                                if (!campaignId) return;
                                const caption = (document.getElementById(`caption-${post.id}`) as HTMLTextAreaElement | null)?.value ?? "";
                                const localTime = (document.getElementById(`schedule-${post.id}`) as HTMLInputElement | null)?.value;
                                setSavingPostId(post.id);
                                try {
                                  const updated = await linkedinApi.patchPost(campaignId, post.id, {
                                    body: caption,
                                    scheduled_at: localTime ? new Date(localTime).toISOString() : undefined,
                                    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
                                  });
                                  setPosts((current) => current.map((item) => item.id === post.id ? { ...item, ...updated } : item));
                                } finally {
                                  setSavingPostId(null);
                                }
                              }}
                              className="justify-self-start rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
                            >
                              {savingPostId === post.id ? "Saving…" : "Save draft changes"}
                            </button>
                          </div>
                        )}

                        {/* CTA */}
                        {post.cta_text && (
                          <div className="text-[11px] text-blue-400 font-mono bg-blue-500/5 p-2 rounded border border-blue-500/10">
                            CTA: {post.cta_text}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* Tab 3: Schedule & Timing */}
              {activeTab === "schedule" && (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800 space-y-3">
                    <div className="flex items-center space-x-2 text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                      <Calendar size={14} className="text-amber-400" />
                      <span>Execution Window & Timestamps</span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      <div className="p-3 rounded-lg bg-zinc-900/60 border border-zinc-800">
                        <span className="text-zinc-400 block text-[11px]">Start Date:</span>
                        <span className="text-zinc-100 font-semibold font-mono mt-0.5 block">
                          {(campaign.schedule as Record<string, any>)?.start_date
                            ? new Date(
                                (campaign.schedule as Record<string, any>).start_date
                              ).toLocaleDateString(undefined, {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                              })
                            : "Immediate / Continuous"}
                        </span>
                      </div>

                      <div className="p-3 rounded-lg bg-zinc-900/60 border border-zinc-800">
                        <span className="text-zinc-400 block text-[11px]">End Date:</span>
                        <span className="text-zinc-100 font-semibold font-mono mt-0.5 block">
                          {(campaign.schedule as Record<string, any>)?.end_date
                            ? new Date(
                                (campaign.schedule as Record<string, any>).end_date
                              ).toLocaleDateString(undefined, {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                              })
                            : "Continuous Sprint"}
                        </span>
                      </div>

                      <div className="p-3 rounded-lg bg-zinc-900/60 border border-zinc-800">
                        <span className="text-zinc-400 block text-[11px]">Timezone:</span>
                        <span className="text-zinc-100 font-semibold font-mono mt-0.5 block">
                          {(campaign.schedule as Record<string, any>)?.timezone || "UTC"}
                        </span>
                      </div>

                      <div className="p-3 rounded-lg bg-zinc-900/60 border border-zinc-800">
                        <span className="text-zinc-400 block text-[11px]">Created At:</span>
                        <span className="text-zinc-100 font-semibold font-mono mt-0.5 block">
                          {new Date(campaign.created_at).toLocaleDateString(undefined, {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                          })}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : null}
        </div>

        {/* Footer */}
        <div className="p-4 sm:p-5 border-t border-zinc-800/80 bg-zinc-900/40 flex items-center justify-between gap-3">
          <div className="text-xs text-zinc-400">
            Press <kbd className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300 font-mono text-[10px]">ESC</kbd> to exit
          </div>

          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-medium text-zinc-300 hover:text-white hover:bg-zinc-800 transition-colors cursor-pointer"
            >
              Close
            </button>

            {campaign && (
              <Link
                href={`/new-campaign?campaign=${campaign.id}`}
                className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition-all cursor-pointer shadow-lg shadow-blue-900/30"
              >
                <span>Launch in AI Chat</span>
                <ArrowRight size={13} />
              </Link>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

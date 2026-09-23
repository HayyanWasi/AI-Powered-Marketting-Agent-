"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ChevronLeft,
  Check,
  Loader2,
  AlertCircle,
  ArrowUp,
  Edit3,
  CalendarClock,
  CalendarX,
  RefreshCw,
  Send,
  Target,
  Users,
  Award,
  TrendingUp,
  Compass,
  Link2,
} from "lucide-react";
import Sidebar from "@/components/shell/Sidebar";
import CampaignBrief from "@/components/campaign/CampaignBrief";
import PostEditor from "@/components/campaign/PostEditor";
import SchedulePostModal from "@/components/campaign/SchedulePostModal";
import { useAuth } from "@/context/AuthContext";
import {
  campaignApi,
  companyApi,
  intakeApi,
  planApi,
  linkedinApi,
  autopilotApi,
  Campaign,
  CompanyProfile,
  LinkedInConnectedAccount,
  CampaignPlanDocument,
  IntakeChecklistState,
} from "@/lib/api";
import { setActiveBrandId } from "@/lib/activeBrand";
import { ChatMessage } from "@/components/campaign/types";

type TabKey = "chat" | "content" | "calendar" | "strategy";

const TABS: { key: TabKey; label: string }[] = [
  { key: "chat", label: "Chat" },
  { key: "content", label: "Content" },
  { key: "calendar", label: "Calendar" },
  { key: "strategy", label: "Strategy brief" },
];

export interface CampaignPostItem {
  id: string;
  campaign_id: string;
  slot_id?: string;
  hook: string;
  body: string;
  cta_text: string;
  full_content: string;
  status: "draft" | "scheduled" | "publishing" | "published" | "failed" | "needs_review";
  scheduled_at?: string;
  timezone?: string;
  media_type?: string;
  media_url?: string;
  unipile_post_id?: string;
  published_at?: string;
  linkedin_account_id?: string;
}

export default function ExistingCampaignPage() {
  const params = useParams();
  const campaignId = params?.campaignId as string;
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();

  // Mode: "existing" — Guaranteed read-only hydration on mount
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [checklist, setChecklist] = useState<IntakeChecklistState | null>(null);
  const [intakeComplete, setIntakeComplete] = useState(false);
  const [plan, setPlan] = useState<CampaignPlanDocument | null>(null);
  const [posts, setPosts] = useState<CampaignPostItem[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [brand, setBrand] = useState<CompanyProfile | null>(null);
  const [connections, setConnections] = useState<LinkedInConnectedAccount[]>([]);

  // Scheduling state
  const [scheduleTarget, setScheduleTarget] = useState<{ post: CampaignPostItem; mode: "schedule" | "reschedule" } | null>(null);
  const [isScheduling, setIsScheduling] = useState(false);
  const [scheduleError, setScheduleError] = useState<string | null>(null);
  const [cancelingId, setCancelingId] = useState<string | null>(null);
  const [scheduleFlash, setScheduleFlash] = useState<string | null>(null);

  // Publish Now state
  const [publishTarget, setPublishTarget] = useState<CampaignPostItem | null>(null);
  const [isPublishingNowId, setIsPublishingNowId] = useState<string | null>(null);
  const [publishNowError, setPublishNowError] = useState<string | null>(null);

  const [tab, setTab] = useState<TabKey>("chat");
  const [isSending, setIsSending] = useState(false);
  const [savedFlash, setSavedFlash] = useState(false);

  // Content editor state
  const [editingPostId, setEditingPostId] = useState<string | null>(null);
  const [isSavingPost, setIsSavingPost] = useState(false);
  const [savePostError, setSavePostError] = useState<string | null>(null);
  const [editSuccessMessage, setEditSuccessMessage] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isSending]);

  // Read-only GET hydration: strictly NO campaign creation, NO planApi.draft, NO LLM generation
  const hydrate = useCallback(async () => {
    if (!user || !campaignId) return;

    setLoading(true);
    setError(null);

    try {
      // 1. Fetch campaign and verify ownership
      const camp = await campaignApi.get(campaignId);
      setCampaign(camp);

      // 2. Synchronize active brand ONLY after campaign ownership is verified
      if (camp.company_profile_id) {
        setActiveBrandId(user.id, camp.company_profile_id);
      }

      // 3. Rehydrate intake, plan, posts, brand and LinkedIn accounts in parallel
      //    with graceful failure handling (any one missing must not blank the page).
      const [historyRes, planRes, postsRes, brandRes, connRes] = await Promise.allSettled([
        intakeApi.getHistory(campaignId),
        planApi.get(campaignId),
        campaignApi.getPosts(campaignId),
        camp.company_profile_id
          ? companyApi.get(camp.company_profile_id)
          : Promise.reject(new Error("no brand")),
        linkedinApi.listConnections(),
      ]);

      const conns = connRes.status === "fulfilled" ? connRes.value || [] : [];
      if (connRes.status === "fulfilled") setConnections(conns);

      if (brandRes.status === "fulfilled") {
        let loadedBrand = brandRes.value;
        const activeConn = conns.find((c) => c.status === "connected");
        const hasValidDefault = Boolean(
          loadedBrand.default_linkedin_account_id &&
            conns.some(
              (c) => c.id === loadedBrand.default_linkedin_account_id && c.status === "connected"
            )
        );
        if (!hasValidDefault && activeConn && loadedBrand?.id) {
          try {
            loadedBrand = await companyApi.setLinkedInAccount(loadedBrand.id, activeConn.id);
          } catch {
            // Non-fatal if auto-binding fails
          }
        }
        setBrand(loadedBrand);
      }

      // Rehydrate intake history
      if (historyRes.status === "fulfilled") {
        const h = historyRes.value;
        setChecklist(h.checklist || null);
        setIntakeComplete(Boolean(h.is_complete));
        if (Array.isArray(h.history) && h.history.length > 0) {
          const mapped: ChatMessage[] = h.history.map((item, idx) => ({
            id: item.id || `msg-${idx}`,
            role: item.role === "user" ? "user" : "assistant",
            content: item.content,
            timestamp: item.created_at
              ? new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
              : "",
          }));
          setMessages(mapped);
        }
      }

      // Rehydrate plan
      if (planRes.status === "fulfilled") {
        setPlan(planRes.value);
      }

      // Rehydrate posts
      if (postsRes.status === "fulfilled") {
        const pList = postsRes.value || [];
        setPosts(
          pList.map((p) => {
            const hook = p.hook || "";
            const body = p.body || p.full_content || "";
            const cta_text = p.cta_text || "";
            const full_content = p.full_content || [hook, body, cta_text].join("\n\n").trim();
            const status = (p.status as CampaignPostItem["status"]) || "draft";
            return {
              id: p.id,
              campaign_id: p.campaign_id || campaignId,
              slot_id: p.slot_id,
              hook,
              body,
              cta_text,
              full_content,
              status,
              scheduled_at: p.scheduled_at,
              timezone: typeof p === "object" && p && "timezone" in p ? String((p as Record<string, unknown>).timezone) : undefined,
              media_type: p.media_type,
              media_url: p.media_url,
              unipile_post_id: p.unipile_post_id,
              published_at: p.published_at,
              linkedin_account_id: p.linkedin_account_id,
            };
          })
        );
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Campaign not found or access denied";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [user, campaignId]);

  useEffect(() => {
    if (!authLoading) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void hydrate();
    }
  }, [authLoading, hydrate]);

  // Resume incomplete chat turn: uses the SAME campaign_id, ZERO duplicate creation
  const handleSendMessage = async (promptText: string) => {
    if (isSending || !user || !campaignId) return;

    const now = () =>
      new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: promptText,
      timestamp: now(),
    };
    const assistantId = `assistant-${Date.now()}`;
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      timestamp: now(),
      isThinking: true,
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setIsSending(true);

    try {
      const res = await intakeApi.sendMessage(campaignId, promptText);
      setChecklist(res.checklist);
      setIntakeComplete(Boolean(res.is_complete));
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, isThinking: false, content: res.reply }
            : m
        )
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to send message";
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, isThinking: false, content: `Error: ${msg}` }
            : m
        )
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleSaveDraft = () => {
    setSavedFlash(true);
    setTimeout(() => setSavedFlash(false), 1600);
  };

  const handleStartEdit = (postId: string) => {
    if (editingPostId && editingPostId !== postId) {
      const confirmSwitch = window.confirm(
        "You have a post editor open. Discard any unsaved edits and switch posts?"
      );
      if (!confirmSwitch) return;
    }
    setSavePostError(null);
    setEditingPostId(postId);
  };

  const handleCancelEdit = () => {
    setEditingPostId(null);
    setSavePostError(null);
  };

  const handleSavePost = async (
    postId: string,
    fields: { hook: string; body: string; cta_text: string }
  ) => {
    if (!campaignId || isSavingPost) return;
    setIsSavingPost(true);
    setSavePostError(null);
    try {
      // Send ONLY hook, body, and cta_text — no schedule, no account, no media
      const updatedPost = await linkedinApi.patchPost(campaignId, postId, {
        hook: fields.hook,
        body: fields.body,
        cta_text: fields.cta_text,
      });

      // Replace canonical post in state with backend response
      setPosts((prev) =>
        prev.map((p) => {
          if (p.id !== postId) return p;
          const hook = updatedPost.hook ?? fields.hook;
          const body = updatedPost.body ?? fields.body;
          const cta_text = updatedPost.cta_text ?? fields.cta_text;
          const full_content =
            updatedPost.full_content ??
            `${hook}\n\n${body}\n\n${cta_text}`.trim();
          const status =
            (updatedPost.status as CampaignPostItem["status"]) ?? p.status;
          return {
            ...p,
            hook,
            body,
            cta_text,
            full_content,
            status,
            scheduled_at: updatedPost.scheduled_at ?? p.scheduled_at,
            timezone: updatedPost.timezone ?? p.timezone,
          };
        })
      );

      setEditingPostId(null);
      setEditSuccessMessage("Post updated successfully.");
      setTimeout(() => setEditSuccessMessage(null), 3500);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to save post changes.";
      setSavePostError(message);
    } finally {
      setIsSavingPost(false);
    }
  };

  const applyPostUpdate = (updated: Partial<CampaignPostItem> & { id: string }) => {
    setPosts((prev) =>
      prev.map((p) => (p.id === updated.id ? { ...p, ...updated } : p))
    );
  };

  const flash = (msg: string) => {
    setScheduleFlash(msg);
    setTimeout(() => setScheduleFlash(null), 3500);
  };

  const handleConfirmSchedule = async (isoUtc: string, timezone: string) => {
    if (!scheduleTarget || !campaignId) return;
    setIsScheduling(true);
    setScheduleError(null);
    try {
      const { post, mode } = scheduleTarget;
      const updated =
        mode === "schedule"
          ? await linkedinApi.schedulePost(campaignId, post.id, isoUtc, timezone)
          : await linkedinApi.reschedulePost(campaignId, post.id, isoUtc, timezone);
      applyPostUpdate({
        id: post.id,
        status: (updated.status as CampaignPostItem["status"]) ?? "scheduled",
        scheduled_at: updated.scheduled_at ?? isoUtc,
        timezone: updated.timezone ?? timezone,
      });
      setScheduleTarget(null);
      flash(mode === "schedule" ? "Post scheduled." : "Schedule updated.");
    } catch (err: unknown) {
      setScheduleError(err instanceof Error ? err.message : "Could not schedule the post.");
    } finally {
      setIsScheduling(false);
    }
  };

  const handleCancelSchedule = async (post: CampaignPostItem) => {
    if (!campaignId) return;
    if (!window.confirm("Cancel this schedule? The post returns to draft and will not publish.")) return;
    setCancelingId(post.id);
    try {
      const updated = await linkedinApi.cancelSchedule(campaignId, post.id);
      applyPostUpdate({
        id: post.id,
        status: (updated.status as CampaignPostItem["status"]) ?? "draft",
        scheduled_at: updated.scheduled_at ?? undefined,
      });
      flash("Schedule cancelled. Post returned to draft.");
    } catch (err: unknown) {
      flash(err instanceof Error ? err.message : "Could not cancel the schedule.");
    } finally {
      setCancelingId(null);
    }
  };

  const handlePublishNowConfirm = async () => {
    if (!publishTarget || !campaignId) return;
    const targetPost = publishTarget;
    setIsPublishingNowId(targetPost.id);
    setPublishNowError(null);
    try {
      const res = await autopilotApi.publishNow(targetPost.id);
      if (!res.success) {
        throw new Error(res.error || "Publishing failed.");
      }
      // Replace the local post with the complete canonical backend response
      const canonical = (res.post || {}) as Partial<CampaignPostItem>;
      applyPostUpdate({
        id: targetPost.id,
        status: (canonical.status as CampaignPostItem["status"]) || "published",
        unipile_post_id: canonical.unipile_post_id || res.unipile_post_id,
        published_at: canonical.published_at || res.published_at,
        linkedin_account_id: canonical.linkedin_account_id || res.linkedin_account_id,
        scheduled_at: canonical.scheduled_at ?? undefined,
        timezone: canonical.timezone ?? targetPost.timezone,
        hook: canonical.hook ?? targetPost.hook,
        body: canonical.body ?? targetPost.body,
        cta_text: canonical.cta_text ?? targetPost.cta_text,
        full_content: canonical.full_content ?? targetPost.full_content,
      });
      setPublishTarget(null);
      flash("Post published to LinkedIn!");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to publish post.";
      setPublishNowError(msg);
      // Re-hydrate to ensure local UI is in sync with server state
      void hydrate();
    } finally {
      setIsPublishingNowId(null);
    }
  };

  const activeLinkedInAccount =
    connections.find((c) => c.id === brand?.default_linkedin_account_id && c.status === "connected") ||
    connections.find((c) => c.status === "connected");

  const brandAccountName = (() => {
    if (!activeLinkedInAccount) return "the brand's LinkedIn account";
    return `${activeLinkedInAccount.provider || "LinkedIn"} account ·••${activeLinkedInAccount.unipile_account_id.slice(-6)}`;
  })();
  const brandHasConnectedAccount = Boolean(
    brand?.default_linkedin_account_id &&
      connections.some(
        (c) => c.id === brand?.default_linkedin_account_id && c.status === "connected"
      )
  );

  const campaignTitle = campaign?.name || checklist?.campaign_name || "Campaign Workspace";
  const hasPosts = posts.length > 0;
  const isInitial = messages.length === 0;
  const calendarPosts = posts
    .filter((p) => Boolean(p.scheduled_at))
    .sort((a, b) => new Date(a.scheduled_at || 0).getTime() - new Date(b.scheduled_at || 0).getTime());

  return (
    <div className="flex h-screen bg-[#F8FBFC] text-[#18222D] overflow-hidden font-sans">
      <Sidebar active="campaigns" />

      <main className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="h-14 shrink-0 border-b border-[#DCE6EC] bg-white flex items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-2 min-w-0">
            <button
              type="button"
              onClick={() => router.push("/campaigns")}
              className="inline-flex items-center gap-1 text-[13px] text-[#52606B] hover:text-[#18222D] rounded px-1.5 py-1 hover:bg-[#F8FBFC] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#187CA4]/30"
            >
              <ChevronLeft size={15} /> Campaigns
            </button>
            <span className="text-[#DCE6EC]">/</span>
            <span className="text-[14px] font-semibold text-[#18222D] truncate">
              {campaignTitle}
            </span>
            <span className="ml-1 text-[10.5px] font-semibold uppercase tracking-wide text-[#52606B] border border-[#DCE6EC] rounded px-1.5 py-0.5">
              {hasPosts ? "Generated" : campaign?.state || "Draft"}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleSaveDraft}
              className="inline-flex items-center gap-1.5 text-[13px] font-medium text-[#52606B] hover:text-[#18222D] border border-[#DCE6EC] rounded-[8px] px-3 py-1.5 hover:bg-[#F8FBFC] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#187CA4]/30"
            >
              {savedFlash ? (
                <>
                  <Check size={14} className="text-[#2B8A3E]" /> Saved
                </>
              ) : (
                "Save draft"
              )}
            </button>
            <button
              type="button"
              onClick={() => router.push("/campaigns")}
              className="text-[13px] font-medium text-[#52606B] hover:text-[#18222D] rounded-[8px] px-3 py-1.5 hover:bg-[#F8FBFC] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#187CA4]/30"
            >
              Exit
            </button>
          </div>
        </header>

        {/* Loading State */}
        {loading && (
          <div className="flex-1 flex flex-col items-center justify-center py-24 text-[#52606B]">
            <Loader2 size={26} className="animate-spin text-[#187CA4] mb-3" />
            <p className="text-[13.5px]">Loading campaign workspace…</p>
          </div>
        )}

        {/* Fatal Error State (404/403 or campaign not found) */}
        {!loading && error && (
          <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
            <div className="w-12 h-12 rounded-full bg-[#FDF7F7] border border-[#F5C6CB] text-[#DC3545] grid place-items-center mb-4">
              <AlertCircle size={24} />
            </div>
            <h2 className="text-[18px] font-semibold text-[#18222D]">Campaign Not Found</h2>
            <p className="text-[13.5px] text-[#52606B] mt-1 max-w-md">
              {error || "This campaign does not exist or you do not have permission to view it."}
            </p>
            <button
              type="button"
              onClick={() => router.push("/campaigns")}
              className="mt-6 inline-flex items-center gap-2 rounded-[8px] bg-[#187CA4] hover:bg-[#136384] text-white text-[13.5px] font-semibold px-4 py-2 transition-colors"
            >
              Back to Campaigns
            </button>
          </div>
        )}

        {/* Hydrated Workspace */}
        {!loading && !error && campaign && (
          <>
            {/* Tabs */}
            <div className="shrink-0 border-b border-[#DCE6EC] bg-white px-4 sm:px-6">
              <div className="flex gap-6" role="tablist" aria-label="Campaign sections">
                {TABS.map((t) => (
                  <button
                    key={t.key}
                    role="tab"
                    aria-selected={tab === t.key}
                    onClick={() => setTab(t.key)}
                    className={`relative py-3 text-[13.5px] font-medium transition-colors focus-visible:outline-none ${
                      tab === t.key ? "text-[#187CA4]" : "text-[#52606B] hover:text-[#18222D]"
                    }`}
                  >
                    {t.label}
                    {tab === t.key && (
                      <span className="absolute left-0 right-0 -bottom-px h-0.5 bg-[#187CA4] rounded-full" />
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Tab Body */}
            <div className="flex-1 flex min-h-0">
              <div className="flex-1 flex flex-col min-w-0">
                {tab === "chat" && (
                  <>
                    <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 sm:px-8 py-6">
                      <div className="max-w-2xl mx-auto">
                        {isInitial ? (
                          <div className="pt-10 text-center">
                            <h2 className="text-[20px] font-semibold text-[#18222D]">
                              Campaign Intake Conversation
                            </h2>
                            <p className="text-[13.5px] text-[#52606B] mt-1.5 max-w-md mx-auto">
                              Continue shaping your brief or review the saved strategist recommendations.
                            </p>
                          </div>
                        ) : (
                          <div className="space-y-6">
                            {messages.map((m) =>
                              m.role === "user" ? (
                                <div key={m.id}>
                                  <p className="text-[11px] font-semibold uppercase tracking-wide text-[#52606B] mb-1.5">
                                    You
                                  </p>
                                  <div className="rounded-[12px] bg-[#EDF6F9] border border-[#DCE6EC] px-4 py-3 text-[14px] leading-relaxed text-[#18222D] whitespace-pre-wrap">
                                    {m.content}
                                  </div>
                                </div>
                              ) : (
                                <div key={m.id}>
                                  <p className="text-[11px] font-semibold uppercase tracking-wide text-[#187CA4] mb-1.5">
                                    Campaign strategist
                                  </p>
                                  {m.isThinking && !m.content ? (
                                    <p className="text-[14px] text-[#52606B] flex items-center gap-2">
                                      <Loader2 size={14} className="animate-spin text-[#187CA4]" /> Thinking…
                                    </p>
                                  ) : (
                                    <div className="text-[14px] leading-relaxed text-[#18222D] whitespace-pre-wrap">
                                      {m.content}
                                    </div>
                                  )}
                                </div>
                              )
                            )}

                            {intakeComplete && !hasPosts && (
                              <div className="rounded-[12px] border border-[#DCE6EC] bg-white px-4 py-4 flex items-center justify-between gap-4 shadow-sm">
                                <div>
                                  <p className="text-[14px] font-semibold text-[#18222D]">
                                    Campaign intake complete
                                  </p>
                                  <p className="text-[12.5px] text-[#52606B] mt-0.5">
                                    Strategy brief is ready. Review details in the Strategy tab.
                                  </p>
                                </div>
                              </div>
                            )}

                            {hasPosts && (
                              <div className="rounded-[12px] border border-[#C3FAC7] bg-[#EBFBEE] px-4 py-3.5 flex items-center justify-between gap-4">
                                <p className="text-[13px] text-[#2B8A3E] font-medium">
                                  Generated LinkedIn posts are available in the Content tab.
                                </p>
                                <button
                                  type="button"
                                  onClick={() => setTab("content")}
                                  className="text-[12.5px] font-semibold text-[#187CA4] hover:underline shrink-0"
                                >
                                  View Content →
                                </button>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Composer for continuing intake if incomplete */}
                    <div className="shrink-0 border-t border-[#DCE6EC] bg-white px-4 sm:px-8 py-3">
                      <Composer onSend={handleSendMessage} disabled={isSending} />
                    </div>
                  </>
                )}

                {tab === "content" && (
                  <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6">
                    <div className="max-w-2xl mx-auto space-y-4">
                      {editSuccessMessage && (
                        <div
                          role="status"
                          className="rounded-[8px] border border-[#C3FAC7] bg-[#EBFBEE] p-3 text-[13px] text-[#2B8A3E] font-medium flex items-center gap-2"
                        >
                          <Check className="w-4 h-4 shrink-0" />
                          <span>{editSuccessMessage}</span>
                        </div>
                      )}

                      {scheduleFlash && (
                        <div
                          role="status"
                          className="rounded-[8px] border border-[#DCE6EC] bg-[#EDF6F9] p-3 text-[13px] text-[#187CA4] font-medium flex items-center gap-2"
                        >
                          <Check className="w-4 h-4 shrink-0" />
                          <span>{scheduleFlash}</span>
                        </div>
                      )}


                      {posts.length === 0 ? (
                        <div className="pt-16 text-center">
                          <h2 className="text-[16px] font-semibold text-[#18222D]">No content yet</h2>
                          <p className="text-[13.5px] text-[#52606B] mt-1.5 max-w-sm mx-auto">
                            Generated LinkedIn posts will appear here once campaign generation is run.
                          </p>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          {posts.map((p, i) => {
                            const isEditing = editingPostId === p.id;
                            const canonicalContent = (
                              p.full_content ||
                              [p.hook, p.body, p.cta_text].filter(Boolean).join("\n\n")
                            ).trim();
                            const charCount = canonicalContent.length;
                            const wordCount = canonicalContent ? canonicalContent.split(/\s+/).length : 0;

                            if (isEditing) {
                              return (
                                <PostEditor
                                  key={p.id}
                                  post={p}
                                  onSave={(fields) => handleSavePost(p.id, fields)}
                                  onCancel={handleCancelEdit}
                                  isSaving={isSavingPost}
                                  saveError={savePostError}
                                />
                              );
                            }

                            return (
                              <div
                                key={p.id}
                                className="rounded-[12px] border border-[#DCE6EC] bg-white p-5 shadow-sm space-y-3"
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <span className="text-[11px] font-semibold uppercase tracking-wide text-[#52606B]">
                                      Post {i + 1}
                                      {p.media_type === "video" ? " · Video" : ""}
                                    </span>
                                    <span
                                      className={`text-[10.5px] font-medium uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                                        p.status === "published"
                                          ? "bg-[#EBFBEE] text-[#2B8A3E] border-[#C3FAC7]"
                                          : p.status === "publishing"
                                          ? "bg-[#FFF8E1] text-[#B78103] border-[#FFE082]"
                                          : p.status === "scheduled"
                                          ? "bg-[#EDF6F9] text-[#187CA4] border-[#DCE6EC]"
                                          : p.status === "failed"
                                          ? "bg-[#FDF2F2] text-[#D9381E] border-[#F5C2C7]"
                                          : p.status === "needs_review"
                                          ? "bg-[#FFF8E1] text-[#B78103] border-[#FFE082]"
                                          : "bg-[#EDF6F9] text-[#52606B] border-[#DCE6EC]"
                                      }`}
                                    >
                                      {p.status.replace("_", " ")}
                                    </span>
                                  </div>

                                  <div className="flex items-center gap-2">
                                    {p.scheduled_at && (
                                      <span className="text-[11.5px] text-[#52606B]">
                                        {new Date(p.scheduled_at).toLocaleString([], {
                                          month: "short",
                                          day: "numeric",
                                          hour: "numeric",
                                          minute: "2-digit",
                                        })}
                                        {p.status === "scheduled" && p.timezone
                                          ? ` · ${p.timezone.replace(/_/g, " ")}`
                                          : ""}
                                      </span>
                                    )}

                                    {p.status === "draft" && (
                                      <>
                                        <button
                                          type="button"
                                          onClick={() => handleStartEdit(p.id)}
                                          disabled={isPublishingNowId === p.id}
                                          className="inline-flex items-center gap-1 text-[12px] font-medium text-[#187CA4] hover:text-[#146485] hover:bg-[#EDF6F9] px-2.5 py-1 rounded-[6px] border border-[#DCE6EC] transition-colors cursor-pointer disabled:opacity-50"
                                        >
                                          <Edit3 className="w-3.5 h-3.5" />
                                          <span>Edit</span>
                                        </button>
                                        {brandHasConnectedAccount ? (
                                          <>
                                            <button
                                              type="button"
                                              onClick={() => {
                                                setScheduleError(null);
                                                setScheduleTarget({ post: p, mode: "schedule" });
                                              }}
                                              disabled={isPublishingNowId === p.id}
                                              title="Schedule this post"
                                              className="inline-flex items-center gap-1 text-[12px] font-medium text-[#187CA4] hover:text-[#136384] hover:bg-[#EDF6F9] px-2.5 py-1 rounded-[6px] border border-[#DCE6EC] transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                                            >
                                              <CalendarClock className="w-3.5 h-3.5" />
                                              <span>Schedule</span>
                                            </button>
                                            <button
                                              type="button"
                                              onClick={() => {
                                                setPublishNowError(null);
                                                setPublishTarget(p);
                                              }}
                                              disabled={isPublishingNowId === p.id}
                                              title="Publish this post now to LinkedIn"
                                              className="inline-flex items-center gap-1 text-[12px] font-medium text-white bg-[#187CA4] hover:bg-[#136384] px-2.5 py-1 rounded-[6px] transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-[#187CA4]"
                                            >
                                              {isPublishingNowId === p.id ? (
                                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                              ) : (
                                                <Send className="w-3.5 h-3.5" />
                                              )}
                                              <span>Publish now</span>
                                            </button>
                                          </>
                                        ) : (
                                          <button
                                            type="button"
                                            onClick={() => router.push("/prospects?tab=linkedin")}
                                            title="Connect your LinkedIn account in Prospects to publish"
                                            className="inline-flex items-center gap-1 text-[12px] font-medium text-[#187CA4] hover:text-[#136384] hover:bg-[#EDF6F9] px-2.5 py-1 rounded-[6px] border border-[#DCE6EC] transition-colors cursor-pointer"
                                          >
                                            <Link2 className="w-3.5 h-3.5" />
                                            <span>Connect LinkedIn</span>
                                          </button>
                                        )}
                                      </>
                                    )}

                                    {p.status === "scheduled" && (
                                      <>
                                        <button
                                          type="button"
                                          onClick={() => {
                                            setScheduleError(null);
                                            setScheduleTarget({ post: p, mode: "reschedule" });
                                          }}
                                          className="inline-flex items-center gap-1 text-[12px] font-medium text-[#187CA4] hover:text-[#146485] hover:bg-[#EDF6F9] px-2.5 py-1 rounded-[6px] border border-[#DCE6EC] transition-colors cursor-pointer"
                                        >
                                          <RefreshCw className="w-3.5 h-3.5" />
                                          <span>Reschedule</span>
                                        </button>
                                        <button
                                          type="button"
                                          onClick={() => handleCancelSchedule(p)}
                                          disabled={cancelingId === p.id}
                                          className="inline-flex items-center gap-1 text-[12px] font-medium text-[#52606B] hover:text-[#D9381E] hover:bg-[#FDF2F2] px-2.5 py-1 rounded-[6px] border border-[#DCE6EC] transition-colors cursor-pointer disabled:opacity-50"
                                        >
                                          {cancelingId === p.id ? (
                                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                          ) : (
                                            <CalendarX className="w-3.5 h-3.5" />
                                          )}
                                          <span>Cancel</span>
                                        </button>
                                      </>
                                    )}

                                    {(p.status === "failed" || p.status === "needs_review") && (
                                      <button
                                        type="button"
                                        onClick={() => handleStartEdit(p.id)}
                                        className="inline-flex items-center gap-1 text-[12px] font-medium text-[#187CA4] hover:text-[#146485] hover:bg-[#EDF6F9] px-2.5 py-1 rounded-[6px] border border-[#DCE6EC] transition-colors cursor-pointer"
                                      >
                                        <Edit3 className="w-3.5 h-3.5" />
                                        <span>Edit</span>
                                      </button>
                                    )}

                                    {(p.status === "published" || p.status === "publishing") && (
                                      <span
                                        className="text-[11.5px] text-[#52606B]/80 italic"
                                        title={
                                          p.status === "published"
                                            ? "Published posts cannot be edited."
                                            : "Post is currently being published."
                                        }
                                      >
                                        {p.status === "published" ? "Published" : "Publishing"}
                                      </span>
                                    )}
                                  </div>
                                </div>

                                <div className="space-y-2 pt-1 border-t border-[#DCE6EC]/60">
                                  {p.hook ? (
                                    <>
                                      <p className="text-[13.5px] font-semibold text-[#18222D]">
                                        {p.hook}
                                      </p>
                                      <p className="text-[13px] leading-relaxed text-[#18222D] whitespace-pre-wrap">
                                        {p.body}
                                      </p>
                                      {p.cta_text && (
                                        <p className="text-[12.5px] text-[#187CA4] font-medium pt-1">
                                          {p.cta_text}
                                        </p>
                                      )}
                                    </>
                                  ) : (
                                    <p className="text-[13.5px] leading-relaxed text-[#18222D] whitespace-pre-wrap">
                                      {p.full_content}
                                    </p>
                                  )}
                                </div>

                                <div className="pt-2.5 border-t border-[#DCE6EC]/60 flex items-center justify-between text-[11.5px] text-[#52606B]">
                                  <div className="flex items-center gap-2">
                                    <span
                                      className={
                                        charCount > 3000
                                          ? "text-[#D9381E] font-semibold"
                                          : charCount > 2700
                                          ? "text-[#B78103] font-medium"
                                          : "text-[#52606B]"
                                      }
                                    >
                                      {charCount.toLocaleString()} / 3,000 characters
                                    </span>
                                    <span>•</span>
                                    <span>{wordCount.toLocaleString()} words</span>
                                  </div>
                                  {charCount > 3000 && (
                                    <span className="text-[#D9381E] text-[11px] font-medium">
                                      Exceeds LinkedIn limit
                                    </span>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {tab === "calendar" && (
                  <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6">
                    <div className="max-w-2xl mx-auto">
                      <div className="mb-4">
                        <h2 className="text-[16px] font-semibold text-[#18222D]">Schedule</h2>
                        <p className="text-[13px] text-[#52606B] mt-0.5">
                          Planned and scheduled posts for this campaign. Posts marked Planned / Draft require scheduling before automatic publishing.
                        </p>
                      </div>

                      {calendarPosts.length === 0 ? (
                        <div className="pt-12 text-center">
                          <p className="text-[13.5px] text-[#52606B] max-w-sm mx-auto">
                            No posts have a planned or scheduled date yet. Open the Content tab to review and schedule posts.
                          </p>
                        </div>
                      ) : (
                        <ol className="space-y-2.5">
                          {calendarPosts.map((p, i) => {
                            const idx = posts.findIndex((x) => x.id === p.id);
                            const isDraft = p.status === "draft";
                            const isScheduled = p.status === "scheduled";
                            const isPublishing = p.status === "publishing";
                            const isPublished = p.status === "published";
                            const isFailed = p.status === "failed";

                            return (
                              <li
                                key={p.id}
                                className="rounded-[10px] border border-[#DCE6EC] bg-white p-3.5 flex items-center justify-between gap-3"
                              >
                                <div className="flex items-center gap-3 min-w-0 flex-1">
                                  <div className="w-9 h-9 rounded-[8px] bg-[#EDF6F9] border border-[#DCE6EC] grid place-items-center text-[12px] font-semibold text-[#187CA4] shrink-0">
                                    {idx >= 0 ? idx + 1 : i + 1}
                                  </div>
                                  <div className="min-w-0 flex-1">
                                    <p className="text-[13px] font-medium text-[#18222D] truncate">
                                      {p.hook || p.full_content || "LinkedIn post"}
                                    </p>
                                    <p className="text-[11.5px] text-[#52606B] mt-0.5">
                                      {p.scheduled_at
                                        ? new Date(p.scheduled_at).toLocaleString([], {
                                            weekday: "short",
                                            month: "short",
                                            day: "numeric",
                                            hour: "numeric",
                                            minute: "2-digit",
                                          })
                                        : "—"}
                                      {p.timezone
                                        ? ` · ${p.timezone.replace(/_/g, " ")}`
                                        : ""}
                                    </p>
                                  </div>
                                </div>

                                <div className="flex items-center gap-2 shrink-0">
                                  <span
                                    className={`text-[10.5px] font-medium uppercase tracking-wider px-2 py-0.5 rounded-full border shrink-0 ${
                                      isPublished
                                        ? "bg-[#EBFBEE] text-[#2B8A3E] border-[#C3FAC7]"
                                        : isPublishing
                                        ? "bg-[#FFF8E1] text-[#B78103] border-[#FFE082]"
                                        : isScheduled
                                        ? "bg-[#EDF6F9] text-[#187CA4] border-[#DCE6EC]"
                                        : isFailed
                                        ? "bg-[#FDF2F2] text-[#D9381E] border-[#F5C2C7]"
                                        : "bg-[#F8FBFC] text-[#52606B] border-[#DCE6EC]"
                                    }`}
                                  >
                                    {isDraft ? "Planned / Draft" : p.status.replace("_", " ")}
                                  </span>

                                  {isDraft && (
                                    brandHasConnectedAccount ? (
                                      <button
                                        type="button"
                                        onClick={() => {
                                          setScheduleError(null);
                                          setScheduleTarget({ post: p, mode: "schedule" });
                                        }}
                                        title="Schedule this post"
                                        className="inline-flex items-center gap-1 text-[12px] font-medium text-[#187CA4] hover:text-[#136384] hover:bg-[#EDF6F9] px-2.5 py-1 rounded-[6px] border border-[#DCE6EC] transition-colors cursor-pointer"
                                      >
                                        <CalendarClock className="w-3.5 h-3.5" />
                                        <span>Schedule</span>
                                      </button>
                                    ) : (
                                      <button
                                        type="button"
                                        onClick={() => router.push("/prospects?tab=linkedin")}
                                        title="Connect your LinkedIn account in Prospects to schedule"
                                        className="inline-flex items-center gap-1 text-[12px] font-medium text-[#187CA4] hover:text-[#136384] hover:bg-[#EDF6F9] px-2.5 py-1 rounded-[6px] border border-[#DCE6EC] transition-colors cursor-pointer"
                                      >
                                        <Link2 className="w-3.5 h-3.5" />
                                        <span>Connect LinkedIn</span>
                                      </button>
                                    )
                                  )}

                                  {isScheduled && (
                                    <>
                                      <button
                                        type="button"
                                        onClick={() => {
                                          setScheduleError(null);
                                          setScheduleTarget({ post: p, mode: "reschedule" });
                                        }}
                                        className="inline-flex items-center gap-1 text-[12px] font-medium text-[#187CA4] hover:text-[#146485] hover:bg-[#EDF6F9] px-2.5 py-1 rounded-[6px] border border-[#DCE6EC] transition-colors cursor-pointer"
                                      >
                                        <RefreshCw className="w-3.5 h-3.5" />
                                        <span>Reschedule</span>
                                      </button>
                                      <button
                                        type="button"
                                        onClick={() => handleCancelSchedule(p)}
                                        disabled={cancelingId === p.id}
                                        className="inline-flex items-center gap-1 text-[12px] font-medium text-[#52606B] hover:text-[#D9381E] hover:bg-[#FDF2F2] px-2.5 py-1 rounded-[6px] border border-[#DCE6EC] transition-colors cursor-pointer disabled:opacity-50"
                                      >
                                        {cancelingId === p.id ? (
                                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                        ) : (
                                          <CalendarX className="w-3.5 h-3.5" />
                                        )}
                                        <span>Cancel</span>
                                      </button>
                                    </>
                                  )}
                                </div>
                              </li>
                            );
                          })}
                        </ol>
                      )}
                    </div>
                  </div>
                )}

                {tab === "strategy" && (
                  <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6">
                    <div className="max-w-2xl mx-auto space-y-6">
                      {plan ? (
                        <>
                          {/* 1. Title & Executive Summary */}
                          <div className="rounded-[12px] border border-[#DCE6EC] bg-white p-6 shadow-sm space-y-4">
                            <div>
                              <div className="flex items-center gap-2 text-[#187CA4] text-[12px] font-semibold uppercase tracking-wider mb-1">
                                <Award className="w-4 h-4" />
                                <span>Chief Strategist Synthesis</span>
                              </div>
                              <h2 className="text-[18px] font-semibold text-[#18222D]">
                                {plan.title || plan.campaign_name || "Campaign Strategy Brief"}
                              </h2>
                            </div>

                            {plan.executive_summary && (
                              <div className="space-y-1">
                                <h3 className="text-[12px] font-semibold uppercase tracking-wider text-[#52606B]">
                                  Executive Summary
                                </h3>
                                <p className="text-[13.5px] leading-relaxed text-[#18222D] whitespace-pre-wrap">
                                  {plan.executive_summary}
                                </p>
                              </div>
                            )}

                            {plan.core_strategy?.positioning_statement && (
                              <div className="pt-3 border-t border-[#DCE6EC]/60 space-y-1">
                                <h3 className="text-[12px] font-semibold uppercase tracking-wider text-[#52606B]">
                                  Positioning Statement
                                </h3>
                                <p className="text-[13px] leading-relaxed text-[#18222D] italic">
                                  &ldquo;{plan.core_strategy.positioning_statement}&rdquo;
                                </p>
                              </div>
                            )}

                            {(plan.core_strategy?.unique_selling_proposition || plan.core_strategy?.tone_of_voice) && (
                              <div className="pt-3 border-t border-[#DCE6EC]/60 grid grid-cols-1 sm:grid-cols-2 gap-4">
                                {plan.core_strategy?.unique_selling_proposition && (
                                  <div>
                                    <h4 className="text-[11.5px] font-semibold uppercase tracking-wider text-[#52606B]">
                                      Unique Value Proposition
                                    </h4>
                                    <p className="text-[13px] text-[#18222D] mt-0.5">
                                      {plan.core_strategy.unique_selling_proposition}
                                    </p>
                                  </div>
                                )}
                                {plan.core_strategy?.tone_of_voice && (
                                  <div>
                                    <h4 className="text-[11.5px] font-semibold uppercase tracking-wider text-[#52606B]">
                                      Tone of Voice
                                    </h4>
                                    <p className="text-[13px] text-[#18222D] mt-0.5">
                                      {plan.core_strategy.tone_of_voice}
                                    </p>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>

                          {/* 2. Messaging Pillars */}
                          {plan.core_strategy?.messaging_pillars && plan.core_strategy.messaging_pillars.length > 0 && (
                            <div className="rounded-[12px] border border-[#DCE6EC] bg-white p-6 shadow-sm space-y-3">
                              <div className="flex items-center gap-2 text-[#187CA4] text-[12px] font-semibold uppercase tracking-wider">
                                <Target className="w-4 h-4" />
                                <span>Messaging Pillars</span>
                              </div>
                              <ul className="space-y-2.5 pt-1">
                                {plan.core_strategy.messaging_pillars.map((pillar, idx) => (
                                  <li key={idx} className="text-[13px] text-[#18222D] flex items-start gap-2.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-[#187CA4] mt-2 shrink-0" />
                                    <span className="leading-relaxed">{pillar}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* 3. Target Personas */}
                          {plan.core_strategy?.personas && plan.core_strategy.personas.length > 0 && (
                            <div className="rounded-[12px] border border-[#DCE6EC] bg-white p-6 shadow-sm space-y-4">
                              <div className="flex items-center gap-2 text-[#187CA4] text-[12px] font-semibold uppercase tracking-wider">
                                <Users className="w-4 h-4" />
                                <span>Target Personas</span>
                              </div>
                              <div className="grid grid-cols-1 gap-4 pt-1">
                                {plan.core_strategy.personas.map((persona, idx) => (
                                  <div
                                    key={idx}
                                    className="rounded-[10px] bg-[#F8FBFC] border border-[#DCE6EC] p-4 space-y-2"
                                  >
                                    <div className="flex items-center justify-between">
                                      <h4 className="text-[13.5px] font-semibold text-[#18222D]">
                                        {persona.name || `Persona ${idx + 1}`}
                                      </h4>
                                      {persona.demographics && (
                                        <span className="text-[11px] text-[#52606B] font-medium">
                                          {persona.demographics}
                                        </span>
                                      )}
                                    </div>
                                    {persona.description && (
                                      <p className="text-[12.5px] text-[#52606B] leading-relaxed">
                                        {persona.description}
                                      </p>
                                    )}
                                    {persona.pain_points && persona.pain_points.length > 0 && (
                                      <div className="pt-2 border-t border-[#DCE6EC]/60">
                                        <p className="text-[11px] font-semibold uppercase tracking-wider text-[#52606B] mb-1">
                                          Pain Points
                                        </p>
                                        <div className="flex flex-wrap gap-1.5">
                                          {persona.pain_points.map((pp, pIdx) => (
                                            <span
                                              key={pIdx}
                                              className="px-2 py-0.5 rounded bg-white border border-[#DCE6EC] text-[11.5px] text-[#18222D]"
                                            >
                                              {pp}
                                            </span>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                    {persona.motivations && persona.motivations.length > 0 && (
                                      <div className="pt-1">
                                        <p className="text-[11px] font-semibold uppercase tracking-wider text-[#52606B] mb-1">
                                          Motivations
                                        </p>
                                        <div className="flex flex-wrap gap-1.5">
                                          {persona.motivations.map((mot, mIdx) => (
                                            <span
                                              key={mIdx}
                                              className="px-2 py-0.5 rounded bg-[#EDF6F9] border border-[#DCE6EC] text-[11.5px] text-[#187CA4]"
                                            >
                                              {mot}
                                            </span>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* 4. SMART Goals */}
                          {plan.core_strategy?.smart_goals && plan.core_strategy.smart_goals.length > 0 && (
                            <div className="rounded-[12px] border border-[#DCE6EC] bg-white p-6 shadow-sm space-y-3">
                              <div className="flex items-center gap-2 text-[#187CA4] text-[12px] font-semibold uppercase tracking-wider">
                                <TrendingUp className="w-4 h-4" />
                                <span>SMART Goals</span>
                              </div>
                              <div className="grid grid-cols-1 gap-3 pt-1">
                                {plan.core_strategy.smart_goals.map((g, idx) => (
                                  <div
                                    key={idx}
                                    className="rounded-[8px] border border-[#DCE6EC] p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                                  >
                                    <div>
                                      <p className="text-[13px] font-medium text-[#18222D]">
                                        {g.goal}
                                      </p>
                                      {g.metric && (
                                        <p className="text-[11.5px] text-[#52606B] mt-0.5">
                                          Metric: {g.metric}
                                        </p>
                                      )}
                                    </div>
                                    <div className="flex items-center gap-2 shrink-0">
                                      {g.target && (
                                        <span className="px-2 py-0.5 rounded bg-[#EDF6F9] border border-[#DCE6EC] text-[11.5px] font-semibold text-[#187CA4]">
                                          Target: {g.target}
                                        </span>
                                      )}
                                      {g.deadline && (
                                        <span className="text-[11px] text-[#52606B]">
                                          {g.deadline}
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* 5. Competitive Landscape & Differentiation */}
                          {plan.competitive && (
                            <div className="rounded-[12px] border border-[#DCE6EC] bg-white p-6 shadow-sm space-y-4">
                              <div className="flex items-center gap-2 text-[#187CA4] text-[12px] font-semibold uppercase tracking-wider">
                                <Compass className="w-4 h-4" />
                                <span>Competitive Analysis & Differentiation</span>
                              </div>

                              {plan.competitive.differentiation_angle && (
                                <div className="space-y-1">
                                  <h4 className="text-[12px] font-semibold uppercase tracking-wider text-[#52606B]">
                                    Differentiation Angle
                                  </h4>
                                  <p className="text-[13px] leading-relaxed text-[#18222D]">
                                    {plan.competitive.differentiation_angle}
                                  </p>
                                </div>
                              )}

                              {plan.competitive.whitespace_opportunities && plan.competitive.whitespace_opportunities.length > 0 && (
                                <div className="space-y-1.5 pt-2 border-t border-[#DCE6EC]/60">
                                  <h4 className="text-[12px] font-semibold uppercase tracking-wider text-[#52606B]">
                                    Whitespace Opportunities
                                  </h4>
                                  <div className="flex flex-wrap gap-2">
                                    {plan.competitive.whitespace_opportunities.map((opp, idx) => (
                                      <span
                                        key={idx}
                                        className="px-2.5 py-1 rounded-[6px] bg-[#EBFBEE] border border-[#C3FAC7] text-[12px] font-medium text-[#2B8A3E]"
                                      >
                                        {opp}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {plan.competitive.landscape && plan.competitive.landscape.length > 0 && (
                                <div className="space-y-2 pt-2 border-t border-[#DCE6EC]/60">
                                  <h4 className="text-[12px] font-semibold uppercase tracking-wider text-[#52606B]">
                                    Competitor Landscape
                                  </h4>
                                  <div className="grid grid-cols-1 gap-3">
                                    {plan.competitive.landscape.map((comp, idx) => (
                                      <div
                                        key={idx}
                                        className="rounded-[8px] bg-[#F8FBFC] border border-[#DCE6EC] p-3.5 space-y-2"
                                      >
                                        <div className="flex items-center justify-between">
                                          <span className="text-[13px] font-semibold text-[#18222D]">
                                            {comp.name}
                                          </span>
                                          {comp.positioning && (
                                            <span className="text-[11.5px] text-[#52606B] italic">
                                              {comp.positioning}
                                            </span>
                                          )}
                                        </div>
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[12px]">
                                          {comp.strengths && comp.strengths.length > 0 && (
                                            <div>
                                              <span className="font-semibold text-[#2B8A3E]">Strengths:</span>{" "}
                                              <span className="text-[#52606B]">{comp.strengths.join(", ")}</span>
                                            </div>
                                          )}
                                          {comp.weaknesses && comp.weaknesses.length > 0 && (
                                            <div>
                                              <span className="font-semibold text-[#D9381E]">Weaknesses:</span>{" "}
                                              <span className="text-[#52606B]">{comp.weaknesses.join(", ")}</span>
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}

                          {/* 6. Measurement & KPIs */}
                          {plan.measurement && (
                            <div className="rounded-[12px] border border-[#DCE6EC] bg-white p-6 shadow-sm space-y-4">
                              <div className="flex items-center gap-2 text-[#187CA4] text-[12px] font-semibold uppercase tracking-wider">
                                <TrendingUp className="w-4 h-4" />
                                <span>Measurement & Target KPIs</span>
                              </div>

                              {plan.measurement.definition_of_success && (
                                <p className="text-[13px] leading-relaxed text-[#52606B]">
                                  {plan.measurement.definition_of_success}
                                </p>
                              )}

                              {plan.measurement.kpis && plan.measurement.kpis.length > 0 && (
                                <div className="space-y-2">
                                  <h4 className="text-[12px] font-semibold uppercase tracking-wider text-[#52606B]">
                                    Target KPIs
                                  </h4>
                                  <div className="flex flex-wrap gap-2">
                                    {plan.measurement.kpis.map((kpi, idx) => {
                                      const label = typeof kpi === "string" ? kpi : `${kpi.name}${kpi.target ? `: ${kpi.target}` : ""}${kpi.funnel_stage ? ` (${kpi.funnel_stage})` : ""}`;
                                      return (
                                        <span
                                          key={idx}
                                          className="px-2.5 py-1 rounded-[6px] bg-[#EDF6F9] border border-[#DCE6EC] text-[#187CA4] text-[12px] font-medium"
                                        >
                                          {label}
                                        </span>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {plan.measurement.tracking_plan && (
                                <div className="pt-2 border-t border-[#DCE6EC]/60">
                                  <h4 className="text-[11.5px] font-semibold uppercase tracking-wider text-[#52606B] mb-0.5">
                                    Tracking Plan
                                  </h4>
                                  <p className="text-[12.5px] text-[#52606B]">
                                    {plan.measurement.tracking_plan}
                                  </p>
                                </div>
                              )}
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="pt-16 text-center">
                          <h2 className="text-[16px] font-semibold text-[#18222D]">No strategy brief generated yet</h2>
                          <p className="text-[13.5px] text-[#52606B] mt-1.5 max-w-sm mx-auto">
                            Complete the intake questions in the Chat tab to generate the full strategic brief.
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Right brief sidebar — only on the Chat tab */}
              {tab === "chat" && (
                <CampaignBrief
                  checklist={checklist}
                  plan={plan}
                  generated={hasPosts}
                />
              )}
            </div>
          </>
        )}
      </main>

      {scheduleTarget && (
        <SchedulePostModal
          title={scheduleTarget.mode === "schedule" ? "Schedule post" : "Reschedule post"}
          postLabel={`Post ${
            posts.findIndex((x) => x.id === scheduleTarget.post.id) + 1
          }`}
          accountName={brandAccountName}
          initialIso={
            scheduleTarget.mode === "reschedule" ? scheduleTarget.post.scheduled_at : undefined
          }
          initialTimezone={scheduleTarget.post.timezone}
          isSaving={isScheduling}
          error={scheduleError}
          onConfirm={handleConfirmSchedule}
          onClose={() => {
            if (!isScheduling) {
              setScheduleTarget(null);
              setScheduleError(null);
            }
          }}
        />
      )}

      {publishTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl border border-[#DCE6EC] space-y-4">
            <div className="space-y-1">
              <h3 className="text-base font-semibold text-[#18222D]">Publish post now?</h3>
              <p className="text-[13px] text-[#52606B]">
                This post will be published immediately to LinkedIn via{" "}
                <span className="font-semibold text-[#18222D]">{brandAccountName}</span>.
              </p>
            </div>

            <div className="rounded-lg bg-[#F8FBFC] border border-[#DCE6EC] p-3 text-[12.5px] text-[#52606B] line-clamp-3 italic">
              &ldquo;{publishTarget.hook || publishTarget.full_content.slice(0, 120)}...&rdquo;
            </div>

            {publishNowError && (
              <div className="rounded-lg bg-[#FDF2F2] border border-[#F5C2C7] p-3 text-[12.5px] text-[#D9381E] flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{publishNowError}</span>
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => {
                  if (!isPublishingNowId) {
                    setPublishTarget(null);
                    setPublishNowError(null);
                  }
                }}
                disabled={Boolean(isPublishingNowId)}
                className="px-3.5 py-1.5 rounded-[8px] text-[13px] font-medium text-[#52606B] hover:text-[#18222D] hover:bg-[#F8FBFC] border border-[#DCE6EC] transition-colors disabled:opacity-50 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handlePublishNowConfirm}
                disabled={Boolean(isPublishingNowId)}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-[8px] text-[13px] font-medium text-white bg-[#187CA4] hover:bg-[#136384] transition-colors disabled:opacity-50 cursor-pointer"
              >
                {isPublishingNowId ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Publishing…</span>
                  </>
                ) : (
                  <>
                    <Send className="w-3.5 h-3.5" />
                    <span>Confirm &amp; Publish</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Composer Component ───────────────────────────────────────────────── */

function Composer({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void;
  disabled: boolean;
}) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  const submit = () => {
    const t = text.trim();
    if (!t || disabled) return;
    onSend(t);
    setText("");
    if (ref.current) ref.current.style.height = "auto";
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="rounded-[14px] border border-[#DCE6EC] bg-white focus-within:border-[#187CA4] focus-within:ring-2 focus-within:ring-[#187CA4]/15 transition-colors px-3.5 py-2.5">
        <textarea
          ref={ref}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          disabled={disabled}
          placeholder="Message your campaign strategist…"
          aria-label="Message your campaign strategist"
          className="w-full bg-transparent text-[14px] text-[#18222D] placeholder-[#52606B]/50 focus:outline-none resize-none leading-relaxed max-h-36"
        />
        <div className="flex items-center justify-end pt-1.5">
          <button
            type="button"
            onClick={submit}
            disabled={!text.trim() || disabled}
            aria-label="Send message"
            className={`inline-flex items-center gap-1.5 rounded-[8px] px-3.5 py-1.5 text-[13px] font-semibold transition-colors ${
              text.trim() && !disabled
                ? "bg-[#187CA4] text-white hover:bg-[#136384]"
                : "bg-[#F1F3F5] text-[#868E96] cursor-not-allowed"
            }`}
          >
            Send <ArrowUp size={14} strokeWidth={2.5} />
          </button>
        </div>
      </div>
      <p className="text-[11px] text-[#52606B]/70 text-center mt-1.5">
        Shift + Return for a new line
      </p>
    </div>
  );
}

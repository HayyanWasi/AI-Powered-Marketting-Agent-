"use client";

import { useState, useEffect, useCallback } from "react";
import Sidebar from "@/components/shell/Sidebar";
import LinkedInConnectPanel from "@/components/prospects/LinkedInConnectPanel";
import { useAuth } from "@/context/AuthContext";
import { getActiveBrandId, setActiveBrandId } from "@/lib/activeBrand";
import {
  companyApi,
  linkedinAccountsApi,
  autopilotApi,
  personasApi,
  reviewQueueApi,
  CompanyProfile,
  LinkedInAccount,
  TargetPersona,
  ReviewComment,
  AutopilotSettings,
  EngagementActivityEvent,
} from "@/lib/api";
import {
  Plus,
  Trash2,
  Loader2,
  X,
  Check,
  Target,
  ThumbsUp,
  MessageSquare,
  UserPlus,
  AlertCircle,
  RefreshCw,
  Edit2,
  CheckCircle2,
  XCircle,
  Clock,
} from "lucide-react";

interface DailyProgress {
  connections_sent: number;
  connections_max: number;
  likes_given: number;
  likes_max: number;
  comments_posted: number;
  comments_max: number;
}

const ZERO_PROGRESS: DailyProgress = {
  connections_sent: 0,
  connections_max: 10,
  likes_given: 0,
  likes_max: 15,
  comments_posted: 0,
  comments_max: 5,
};

type Tab = "personas" | "review" | "activity" | "settings" | "linkedin";

export default function ProspectsPage() {
  const { user } = useAuth();

  // Active brand and canonical connected account state
  const [activeBrand, setActiveBrand] = useState<CompanyProfile | null>(null);
  const [connectedAccount, setConnectedAccount] = useState<LinkedInAccount | null>(null);

  // Active tab state
  const [tab, setTab] = useState<Tab>("personas");

  // Progress & Settings
  const [progress, setProgress] = useState<DailyProgress>(ZERO_PROGRESS);
  const [settings, setSettings] = useState<AutopilotSettings>({
    engagement_enabled: false,
    auto_like_enabled: false,
    auto_comment_generation_enabled: false,
    auto_connect_enabled: false,
    likes_per_day: 15,
    comments_per_day: 5,
    invites_per_day: 10,
    connection_note_template: "",
    timezone: "UTC",
  });
  const [savingSettings, setSavingSettings] = useState(false);
  const [settingsSaved, setSettingsSaved] = useState(false);

  // Personas state
  const [personas, setPersonas] = useState<TargetPersona[]>([]);
  const [personasLoading, setPersonasLoading] = useState(true);
  const [showAddPersona, setShowAddPersona] = useState(false);
  const [editingPersona, setEditingPersona] = useState<TargetPersona | null>(null);

  // Review Queue state
  const [reviewItems, setReviewItems] = useState<ReviewComment[]>([]);
  const [reviewCount, setReviewCount] = useState(0);
  const [actionInProgressId, setActionInProgressId] = useState<string | null>(null);
  const [editedComments, setEditedComments] = useState<Record<string, string>>({});

  // Activity Log state
  const [activities, setActivities] = useState<EngagementActivityEvent[]>([]);
  const [activityLoading, setActivityLoading] = useState(false);

  // ── 1. Canonical Load for Active Brand & Authoritative Connected Account ───
  const loadBrandData = useCallback(async () => {
    if (!user) return;
    try {
      const brandList = await companyApi.list();
      let activeId = getActiveBrandId(user.id);
      if ((!activeId || !brandList.some((b) => b.id === activeId)) && brandList.length > 0) {
        activeId = brandList[0].id;
        setActiveBrandId(user.id, activeId);
      }
      const brand = brandList.find((b) => b.id === activeId) || null;
      setActiveBrand(brand);

      if (!brand) {
        setConnectedAccount(null);
        return;
      }

      const brandId = brand.id;

      // Authoritative Settings & Connected Account from backend
      try {
        const s = await autopilotApi.getSettings(brandId);
        setSettings(s);
        if (s.connected_account && s.connected_account.status === "connected") {
          let acct = s.connected_account as LinkedInAccount;
          if (!acct.account_name) {
            try {
              const allAccounts = await linkedinAccountsApi.list();
              const found = allAccounts.find((a) => a.id === acct.id);
              if (found?.account_name) {
                acct = { ...acct, account_name: found.account_name };
              }
            } catch {
              /* ignore enrichment failure */
            }
          }
          setConnectedAccount(acct);
        } else {
          setConnectedAccount(null);
        }
      } catch {
        setConnectedAccount(null);
      }

      // Load Tracker
      try {
        const t = await autopilotApi.getTracker(brandId);
        if (t.daily_progress) setProgress(t.daily_progress);
      } catch {
        /* fallback to defaults */
      }

      // Load Personas
      setPersonasLoading(true);
      try {
        const pRes = await personasApi.list(brandId);
        setPersonas(pRes.personas || []);
      } catch {
        setPersonas([]);
      } finally {
        setPersonasLoading(false);
      }

      // Load Review Queue
      try {
        const rRes = await reviewQueueApi.list(brandId, "pending_review");
        setReviewItems(rRes.comments || []);
        setReviewCount(rRes.total || 0);
        const map: Record<string, string> = {};
        (rRes.comments || []).forEach((c) => {
          map[c.id] = c.generated_text;
        });
        setEditedComments(map);
      } catch {
        setReviewItems([]);
        setReviewCount(0);
      }
    } catch {
      /* ignore top-level failures */
    }
  }, [user]);

  useEffect(() => {
    const timer = setTimeout(() => {
      void loadBrandData();
    }, 0);
    return () => clearTimeout(timer);
  }, [loadBrandData]);

  // Listen to cross-component brand changes in localStorage
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (user && e.key === `active_company_profile_id:${user.id}`) {
        void loadBrandData();
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [user, loadBrandData]);

  // Load Activity when activity tab is opened
  const loadActivity = useCallback(async () => {
    if (!activeBrand) return;
    setActivityLoading(true);
    try {
      const res = await autopilotApi.getActivity(activeBrand.id, 100);
      setActivities(res.events || []);
    } catch {
      setActivities([]);
    } finally {
      setActivityLoading(false);
    }
  }, [activeBrand]);

  useEffect(() => {
    if (tab === "activity") {
      const timer = setTimeout(() => {
        void loadActivity();
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [tab, loadActivity]);

  // Handle URL query parameters (e.g. returning from OAuth)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("linkedin") || params.get("tab") === "linkedin") {
      const timer = setTimeout(() => {
        setTab("linkedin");
      }, 0);
      return () => clearTimeout(timer);
    }
  }, []);

  // ── 2. Master Toggle & Settings Handlers ─────────────────────────────────
  const handleMasterToggle = async () => {
    if (!activeBrand || !connectedAccount) return;
    const next = !settings.engagement_enabled;
    setSettings((prev) => ({ ...prev, engagement_enabled: next }));
    try {
      await autopilotApi.toggle(next, activeBrand.id);
    } catch {
      setSettings((prev) => ({ ...prev, engagement_enabled: !next }));
    }
  };

  const handleSaveSettings = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!activeBrand) return;
    setSavingSettings(true);
    try {
      const res = await autopilotApi.saveSettings({
        company_profile_id: activeBrand.id,
        engagement_enabled: settings.engagement_enabled,
        auto_like_enabled: settings.auto_like_enabled,
        auto_comment_generation_enabled: settings.auto_comment_generation_enabled,
        auto_connect_enabled: settings.auto_connect_enabled,
        likes_per_day: settings.likes_per_day,
        comments_per_day: settings.comments_per_day,
        invites_per_day: settings.invites_per_day,
        connection_note_template: settings.connection_note_template,
        timezone: settings.timezone,
      });
      setSettings(res);
      setProgress((prev) => ({
        ...prev,
        likes_max: res.likes_per_day,
        comments_max: res.comments_per_day,
        connections_max: res.invites_per_day,
      }));
      setSettingsSaved(true);
      setTimeout(() => setSettingsSaved(false), 2500);
    } catch {
      /* ignore */
    } finally {
      setSavingSettings(false);
    }
  };

  // ── 3. Personas Handlers ────────────────────────────────────────────────
  const handleDeletePersona = async (id: string) => {
    if (!activeBrand) return;
    setPersonas((prev) => prev.filter((p) => p.id !== id));
    try {
      await personasApi.delete(id, activeBrand.id);
    } catch {
      if (activeBrand) {
        personasApi.list(activeBrand.id).then((r) => setPersonas(r.personas || []));
      }
    }
  };

  // ── 4. Review Queue Handlers ────────────────────────────────────────────
  const handleApproveComment = async (id: string) => {
    if (actionInProgressId) return;
    setActionInProgressId(id);
    const finalCommentText = editedComments[id] || "";
    try {
      const res = await reviewQueueApi.approve(id, finalCommentText);
      if (res.success) {
        setReviewItems((prev) => prev.filter((item) => item.id !== id));
        setReviewCount((prev) => Math.max(0, prev - 1));
      } else {
        alert(`Approval status: ${res.status} (${res.error || "Requires manual inspection"})`);
        void loadBrandData();
      }
    } catch (e: unknown) {
      alert(`Approval error: ${(e as Error)?.message || String(e)}`);
      void loadBrandData();
    } finally {
      setActionInProgressId(null);
    }
  };

  const handleRejectComment = async (id: string) => {
    if (actionInProgressId) return;
    setActionInProgressId(id);
    try {
      const res = await reviewQueueApi.reject(id, "Rejected by user");
      if (res.success) {
        setReviewItems((prev) => prev.filter((item) => item.id !== id));
        setReviewCount((prev) => Math.max(0, prev - 1));
      }
    } catch (e: unknown) {
      alert(`Reject error: ${(e as Error)?.message || String(e)}`);
    } finally {
      setActionInProgressId(null);
    }
  };

  const isConnected = !!connectedAccount && connectedAccount.status === "connected";
  const activeCount = personas.filter((p) => p.is_active).length;

  return (
    <div className="flex h-screen bg-[#f6f7f8] text-[#1f2a30] overflow-hidden">
      <Sidebar active="prospects" />

      <main className="flex-1 flex flex-col min-w-0">
        {/* Prospects Header — 2 Rows */}
        <header className="shrink-0 border-b border-[#e6e9ec] bg-white">
          {/* ROW 1: Active Brand & LinkedIn Connection Status */}
          <div className="h-14 flex items-center justify-between px-4 sm:px-6 border-b border-[#f1f3f5]">
            <div className="flex items-center gap-2">
              <span className="text-[12px] uppercase tracking-wider text-[#7a848c] font-semibold">
                Brand:
              </span>
              <span className="text-[13.5px] font-bold text-[#1f2a30] bg-[#f0f4f8] px-2.5 py-1 rounded-md">
                {activeBrand ? activeBrand.company_name : "Loading..."}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  isConnected ? "bg-[#1f8a5b]" : "bg-[#d97706]"
                }`}
              />
              {isConnected ? (
                <span className="text-[13px] font-medium text-[#1f8a5b]">
                  {connectedAccount?.account_name || "LinkedIn Connected"}
                </span>
              ) : (
                <span className="text-[13px] text-[#b45309] font-medium">
                  No connected account
                </span>
              )}
            </div>
          </div>

          {/* ROW 2: Section Tabs */}
          <div
            className="flex items-center gap-6 sm:gap-8 px-4 sm:px-6 overflow-x-auto scrollbar-none"
            role="tablist"
          >
            <TabBtn
              label="Target personas"
              count={personas.length > 0 ? personas.length : undefined}
              active={tab === "personas"}
              onClick={() => setTab("personas")}
            />
            <TabBtn
              label="Review queue"
              count={reviewCount > 0 ? reviewCount : undefined}
              active={tab === "review"}
              onClick={() => setTab("review")}
            />
            <TabBtn
              label="Engagement settings"
              active={tab === "settings"}
              onClick={() => setTab("settings")}
            />
            <TabBtn
              label="Activity log"
              active={tab === "activity"}
              onClick={() => setTab("activity")}
            />
            <TabBtn
              label="LinkedIn account"
              active={tab === "linkedin"}
              onClick={() => setTab("linkedin")}
            />
          </div>
        </header>

        {/* Main Content Area */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 py-5 space-y-5">
            {/* If no connected account, show single canonical persistent banner */}
            {!isConnected && (
              <div className="rounded-[12px] border border-[#fde68a] bg-[#fffbeb] p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <AlertCircle size={20} className="text-[#b45309] shrink-0" />
                  <div>
                    <p className="text-[14px] font-semibold text-[#92400e]">
                      LinkedIn Account Not Connected
                    </p>
                    <p className="text-[12.5px] text-[#b45309] mt-0.5">
                      Engagement automation is safely disabled. Connect a LinkedIn account to enable likes, comments, and connections.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setTab("linkedin")}
                  className="rounded-[8px] bg-[#d97706] hover:bg-[#b45309] text-white text-[13px] font-semibold px-3.5 py-2 shrink-0 transition-colors cursor-pointer"
                >
                  Connect LinkedIn
                </button>
              </div>
            )}

            {/* Automation Master Control & Progress Strip */}
            <div className="rounded-[14px] border border-[#e6e9ec] bg-white px-5 py-4 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <button
                  type="button"
                  role="switch"
                  disabled={!isConnected}
                  aria-checked={settings.engagement_enabled}
                  onClick={handleMasterToggle}
                  className={`flex items-center gap-3 shrink-0 focus-visible:outline-none ${
                    !isConnected ? "opacity-50 cursor-not-allowed" : "cursor-pointer"
                  }`}
                >
                  <span
                    className={`w-10 h-6 rounded-full relative transition-colors ${
                      settings.engagement_enabled ? "bg-[#1f8a5b]" : "bg-[#cdd4d8]"
                    }`}
                  >
                    <span
                      className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all ${
                        settings.engagement_enabled ? "left-[18px]" : "left-0.5"
                      }`}
                    />
                  </span>
                  <div>
                    <span className="text-[14px] font-semibold text-[#1f2a30] block">
                      {settings.engagement_enabled
                        ? "Master Automation Active"
                        : "Master Automation Paused"}
                    </span>
                    <span className="text-[11.5px] text-[#7a848c]">
                      {settings.engagement_enabled
                        ? "Automation sessions run on schedule"
                        : "All background actions halted"}
                    </span>
                  </div>
                </button>
              </div>

              {/* Progress Counters (Fully formatted with denominator and non-empty fallback) */}
              <div className="flex flex-wrap gap-x-6 gap-y-2 items-center">
                <Meter
                  label="Likes"
                  value={progress.likes_given}
                  max={settings.likes_per_day}
                  icon={<ThumbsUp size={13} className="text-[#2f6fd6]" />}
                />
                <Meter
                  label="Comments"
                  value={progress.comments_posted}
                  max={settings.comments_per_day}
                  icon={<MessageSquare size={13} className="text-[#1f8a5b]" />}
                />
                <Meter
                  label="Connections"
                  value={progress.connections_sent}
                  max={settings.invites_per_day}
                  icon={<UserPlus size={13} className="text-[#8b5cf6]" />}
                />
              </div>
            </div>

            {/* TAB CONTENT */}

            {/* 1. Target Personas Tab */}
            {tab === "personas" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between pt-1">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-[17px] font-semibold text-[#1f2a30]">
                        Target personas
                      </h2>
                      <span className="text-[11px] font-medium text-[#5a6771] bg-[#eef1f4] rounded-full px-2 py-0.5">
                        {activeCount} active
                      </span>
                    </div>
                    <p className="text-[13px] text-[#7a848c] mt-0.5">
                      The AI automatically discovers target LinkedIn posts and profiles based on these personas.
                    </p>
                  </div>
                  {/* Only show top Add button when personas exist to prevent duplicate CTA in empty state */}
                  {personas.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setShowAddPersona(true)}
                      className="inline-flex items-center gap-1.5 rounded-[8px] bg-[#2f6fd6] hover:bg-[#255cc0] text-white text-[13px] font-semibold px-3.5 py-2 shadow-sm transition-colors cursor-pointer"
                    >
                      <Plus size={14} /> Add persona
                    </button>
                  )}
                </div>

                {personasLoading ? (
                  <div className="flex items-center gap-2 text-[13px] text-[#8a949c] py-12 justify-center">
                    <Loader2 size={16} className="animate-spin" /> Loading personas…
                  </div>
                ) : personas.length === 0 ? (
                  <div className="rounded-[14px] border border-dashed border-[#cfd6da] bg-white p-10 text-center">
                    <div className="w-12 h-12 rounded-full bg-[#f4f6f8] grid place-items-center mx-auto mb-3 text-[#7a848c]">
                      <Target size={22} />
                    </div>
                    <h3 className="text-[16px] font-semibold text-[#1f2a30]">
                      No target personas defined
                    </h3>
                    <p className="text-[13px] text-[#7a848c] mt-1.5 max-w-md mx-auto">
                      Define a persona with target keywords (e.g. &quot;SaaS Founder CEO&quot;) so the AI knows who to engage with. Automation safely pauses when zero personas exist.
                    </p>
                    <button
                      type="button"
                      onClick={() => setShowAddPersona(true)}
                      className="mt-4 inline-flex items-center gap-1.5 rounded-[8px] bg-[#2f6fd6] hover:bg-[#255cc0] text-white text-[13px] font-semibold px-4 py-2 cursor-pointer"
                    >
                      <Plus size={14} /> Create your first persona
                    </button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {personas.map((p) => (
                      <PersonaCard
                        key={p.id}
                        persona={p}
                        onEdit={(p) => setEditingPersona(p)}
                        onDelete={handleDeletePersona}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 2. Review Queue Tab */}
            {tab === "review" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between pt-1">
                  <div>
                    <h2 className="text-[17px] font-semibold text-[#1f2a30]">
                      Comment Review Queue
                    </h2>
                    <p className="text-[13px] text-[#7a848c] mt-0.5">
                      Every AI-generated comment requires human approval before dispatch. You can edit the text before approving.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={loadBrandData}
                    className="inline-flex items-center gap-1.5 text-[13px] font-medium text-[#5a6771] hover:text-[#1f2a30] px-3 py-1.5 rounded-[8px] border border-[#dfe4e7] bg-white hover:bg-[#f4f6f7] cursor-pointer"
                  >
                    <RefreshCw size={13} /> Refresh
                  </button>
                </div>

                {reviewItems.length === 0 ? (
                  <div className="rounded-[14px] border border-[#e6e9ec] bg-white p-12 text-center shadow-sm">
                    <div className="w-12 h-12 rounded-full bg-[#eef1f4] grid place-items-center mx-auto mb-3 text-[#7a848c]">
                      <CheckCircle2 size={24} className="text-[#1f8a5b]" />
                    </div>
                    <h3 className="text-[16px] font-semibold text-[#1f2a30]">
                      Review queue is clear
                    </h3>
                    <p className="text-[13.5px] text-[#7a848c] mt-1.5 max-w-sm mx-auto">
                      When auto-comment generation is enabled, new comment candidates will appear here for your review and approval.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {reviewItems.map((item) => (
                      <div
                        key={item.id}
                        className="rounded-[14px] border border-[#e6e9ec] bg-white p-5 shadow-sm space-y-3"
                      >
                        <div className="flex items-center justify-between text-[12.5px] text-[#7a848c]">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-[#2f6fd6] bg-[#eff6ff] px-2 py-0.5 rounded">
                              {item.persona_label || "Audience Persona"}
                            </span>
                            {item.target_author_name && (
                              <span>Post author: <strong>{item.target_author_name}</strong></span>
                            )}
                          </div>
                          <span className="text-[11.5px] bg-[#fef3c7] text-[#92400e] px-2 py-0.5 rounded font-medium">
                            Requires Manual Review
                          </span>
                        </div>

                        {item.target_post_snippet && (
                          <div className="bg-[#f8fafc] border-l-4 border-[#cbd5e1] p-3 rounded text-[13px] text-[#475569] italic">
                            &quot;{item.target_post_snippet}&quot;
                          </div>
                        )}

                        <div>
                          <label className="block text-[12.5px] font-medium text-[#334155] mb-1.5">
                            Final Comment Text (Editable):
                          </label>
                          <textarea
                            rows={3}
                            value={editedComments[item.id] ?? item.generated_text}
                            onChange={(e) =>
                              setEditedComments((prev) => ({
                                ...prev,
                                [item.id]: e.target.value,
                              }))
                            }
                            className="w-full rounded-[9px] border border-[#dfe4e7] p-3 text-[13.5px] focus:outline-none focus:border-[#2f6fd6] focus:ring-2 focus:ring-[#2f6fd6]/15 font-sans"
                            placeholder="Edit comment before approving..."
                          />
                        </div>

                        <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-[#f1f5f9]">
                          <button
                            type="button"
                            onClick={() => handleRejectComment(item.id)}
                            disabled={actionInProgressId === item.id}
                            className="inline-flex items-center gap-1.5 rounded-[8px] border border-[#dfe4e7] bg-white text-[#5a6771] text-[13px] font-medium px-3.5 py-2 hover:bg-[#f4f6f7] disabled:opacity-50 transition-colors cursor-pointer"
                          >
                            <X size={14} /> Reject
                          </button>
                          <button
                            type="button"
                            onClick={() => handleApproveComment(item.id)}
                            disabled={actionInProgressId === item.id}
                            className="inline-flex items-center gap-1.5 rounded-[8px] bg-[#1f8a5b] hover:bg-[#166534] text-white text-[13px] font-semibold px-4 py-2 disabled:opacity-50 transition-colors shadow-sm cursor-pointer"
                          >
                            {actionInProgressId === item.id ? (
                              <Loader2 size={14} className="animate-spin" />
                            ) : (
                              <Check size={14} />
                            )}
                            Approve &amp; Send
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 3. Engagement Settings Tab (Restored toggle switches, daily caps & styling) */}
            {tab === "settings" && (
              <form onSubmit={handleSaveSettings} className="space-y-6">
                <div className="pt-1 flex items-center justify-between">
                  <div>
                    <h2 className="text-[17px] font-semibold text-[#1f2a30]">
                      Brand Engagement Settings
                    </h2>
                    <p className="text-[13px] text-[#7a848c] mt-0.5">
                      Configure safety limits and automation toggles for {activeBrand?.company_name}. Settings persist to database.
                    </p>
                  </div>
                  {settingsSaved && (
                    <span className="text-[13px] text-[#1f8a5b] font-medium flex items-center gap-1">
                      <Check size={14} /> Settings saved!
                    </span>
                  )}
                </div>

                {/* Auto Likes */}
                <div className="rounded-[14px] border border-[#e6e9ec] bg-white p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-lg bg-[#eff6ff] text-[#2f6fd6] grid place-items-center">
                        <ThumbsUp size={18} />
                      </div>
                      <div>
                        <h3 className="text-[14.5px] font-semibold text-[#1f2a30]">
                          Auto Likes
                        </h3>
                        <p className="text-[12.5px] text-[#7a848c]">
                          Automatically likes posts authored by target personas.
                        </p>
                      </div>
                    </div>
                    <ToggleSwitch
                      checked={settings.auto_like_enabled}
                      disabled={!isConnected}
                      onChange={(checked) =>
                        setSettings((prev) => ({ ...prev, auto_like_enabled: checked }))
                      }
                      activeColor="bg-[#2f6fd6]"
                    />
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-1.5 text-[13px]">
                      <span className="font-medium text-[#475569]">Daily limit (likes)</span>
                      <span className="font-bold text-[#2f6fd6]">{settings.likes_per_day}</span>
                    </div>
                    <input
                      type="range"
                      min={1}
                      max={50}
                      value={settings.likes_per_day}
                      onChange={(e) =>
                        setSettings((prev) => ({
                          ...prev,
                          likes_per_day: Number(e.target.value),
                        }))
                      }
                      className="w-full accent-[#2f6fd6] cursor-pointer"
                    />
                  </div>
                </div>

                {/* Auto Comments */}
                <div className="rounded-[14px] border border-[#e6e9ec] bg-white p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-lg bg-[#ecfdf5] text-[#1f8a5b] grid place-items-center">
                        <MessageSquare size={18} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-[14.5px] font-semibold text-[#1f2a30]">
                            Auto Comments
                          </h3>
                          <span className="text-[11px] font-semibold bg-[#fef3c7] text-[#92400e] px-2 py-0.5 rounded">
                            Requires Manual Review
                          </span>
                        </div>
                        <p className="text-[12.5px] text-[#7a848c]">
                          AI drafts comments for target posts. Comments NEVER send automatically.
                        </p>
                      </div>
                    </div>
                    <ToggleSwitch
                      checked={settings.auto_comment_generation_enabled}
                      disabled={!isConnected}
                      onChange={(checked) =>
                        setSettings((prev) => ({
                          ...prev,
                          auto_comment_generation_enabled: checked,
                        }))
                      }
                      activeColor="bg-[#1f8a5b]"
                    />
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-1.5 text-[13px]">
                      <span className="font-medium text-[#475569]">
                        Daily candidate limit (comments)
                      </span>
                      <span className="font-bold text-[#1f8a5b]">
                        {settings.comments_per_day}
                      </span>
                    </div>
                    <input
                      type="range"
                      min={1}
                      max={20}
                      value={settings.comments_per_day}
                      onChange={(e) =>
                        setSettings((prev) => ({
                          ...prev,
                          comments_per_day: Number(e.target.value),
                        }))
                      }
                      className="w-full accent-[#1f8a5b] cursor-pointer"
                    />
                  </div>
                </div>

                {/* Auto Connections */}
                <div className="rounded-[14px] border border-[#e6e9ec] bg-white p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-lg bg-[#f5f3ff] text-[#8b5cf6] grid place-items-center">
                        <UserPlus size={18} />
                      </div>
                      <div>
                        <h3 className="text-[14.5px] font-semibold text-[#1f2a30]">
                          Auto Connection Requests
                        </h3>
                        <p className="text-[12.5px] text-[#7a848c]">
                          Sends invites to target profiles with relation checks.
                        </p>
                      </div>
                    </div>
                    <ToggleSwitch
                      checked={settings.auto_connect_enabled}
                      disabled={!isConnected}
                      onChange={(checked) =>
                        setSettings((prev) => ({
                          ...prev,
                          auto_connect_enabled: checked,
                        }))
                      }
                      activeColor="bg-[#8b5cf6]"
                    />
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-1.5 text-[13px]">
                      <span className="font-medium text-[#475569]">
                        Daily limit (invitations)
                      </span>
                      <span className="font-bold text-[#8b5cf6]">
                        {settings.invites_per_day}
                      </span>
                    </div>
                    <input
                      type="range"
                      min={1}
                      max={30}
                      value={settings.invites_per_day}
                      onChange={(e) =>
                        setSettings((prev) => ({
                          ...prev,
                          invites_per_day: Number(e.target.value),
                        }))
                      }
                      className="w-full accent-[#8b5cf6] cursor-pointer"
                    />
                  </div>
                  <div>
                    <label className="block text-[12.5px] font-medium text-[#334155] mb-1">
                      Connection Note Template (Optional):
                    </label>
                    <input
                      type="text"
                      value={settings.connection_note_template}
                      onChange={(e) =>
                        setSettings((prev) => ({
                          ...prev,
                          connection_note_template: e.target.value,
                        }))
                      }
                      placeholder="Hi {first_name}, I saw your work and would love to connect!"
                      className="w-full rounded-[8px] border border-[#dfe4e7] px-3 py-2 text-[13.5px] focus:outline-none focus:border-[#2f6fd6]"
                    />
                    <p className="text-[11.5px] text-[#94a3b8] mt-1">
                      Leave blank to send invites without a note. Use <code>{"{first_name}"}</code> for personalization.
                    </p>
                  </div>
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    disabled={savingSettings || !isConnected}
                    className="inline-flex items-center gap-2 rounded-[8px] bg-[#2f6fd6] hover:bg-[#255cc0] text-white text-[13.5px] font-semibold px-5 py-2.5 disabled:opacity-50 shadow-sm transition-colors cursor-pointer"
                  >
                    {savingSettings ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                    Save Engagement Settings
                  </button>
                </div>
              </form>
            )}

            {/* 4. Activity Log Tab */}
            {tab === "activity" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between pt-1">
                  <div>
                    <h2 className="text-[17px] font-semibold text-[#1f2a30]">
                      Engagement Activity Feed
                    </h2>
                    <p className="text-[13px] text-[#7a848c] mt-0.5">
                      Authoritative event history from database log (likes, comments, and connection requests).
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={loadActivity}
                    disabled={activityLoading}
                    className="inline-flex items-center gap-1.5 text-[13px] font-medium text-[#5a6771] hover:text-[#1f2a30] px-3 py-1.5 rounded-[8px] border border-[#dfe4e7] bg-white hover:bg-[#f4f6f7] cursor-pointer"
                  >
                    {activityLoading ? (
                      <Loader2 size={13} className="animate-spin" />
                    ) : (
                      <RefreshCw size={13} />
                    )}
                    Refresh Feed
                  </button>
                </div>

                {activityLoading ? (
                  <div className="flex items-center gap-2 text-[13px] text-[#8a949c] py-12 justify-center">
                    <Loader2 size={16} className="animate-spin" /> Loading activity log…
                  </div>
                ) : activities.length === 0 ? (
                  <div className="rounded-[14px] border border-[#e6e9ec] bg-white p-12 text-center shadow-sm">
                    <div className="w-12 h-12 rounded-full bg-[#f1f5f9] grid place-items-center mx-auto mb-3 text-[#64748b]">
                      <Clock size={22} />
                    </div>
                    <h3 className="text-[16px] font-semibold text-[#1f2a30]">
                      No activity recorded yet
                    </h3>
                    <p className="text-[13px] text-[#7a848c] mt-1.5 max-w-sm mx-auto">
                      Actions executed by the scheduler or approved comments will appear here in real-time.
                    </p>
                  </div>
                ) : (
                  <div className="rounded-[14px] border border-[#e6e9ec] bg-white overflow-hidden shadow-sm">
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse text-[13px]">
                        <thead>
                          <tr className="border-b border-[#e2e8f0] bg-[#f8fafc] text-[#475569] font-medium">
                            <th className="py-3 px-4">Action</th>
                            <th className="py-3 px-4">Target</th>
                            <th className="py-3 px-4">Status</th>
                            <th className="py-3 px-4">Details</th>
                            <th className="py-3 px-4">Timestamp</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#f1f5f9]">
                          {activities.map((act) => (
                            <tr key={act.id} className="hover:bg-[#f8fafc] transition-colors">
                              <td className="py-3 px-4 font-semibold">
                                {act.action_type === "like" && (
                                  <span className="inline-flex items-center gap-1.5 text-[#2563eb]">
                                    <ThumbsUp size={13} /> Like
                                  </span>
                                )}
                                {act.action_type === "comment" && (
                                  <span className="inline-flex items-center gap-1.5 text-[#16a34a]">
                                    <MessageSquare size={13} /> Comment
                                  </span>
                                )}
                                {act.action_type === "connection_request" && (
                                  <span className="inline-flex items-center gap-1.5 text-[#7c3aed]">
                                    <UserPlus size={13} /> Connection
                                  </span>
                                )}
                              </td>
                              <td className="py-3 px-4 font-mono text-[12px] text-[#64748b]">
                                {act.target_post_id ? (
                                  <span>Post: {act.target_post_id.slice(0, 14)}…</span>
                                ) : act.target_profile_id ? (
                                  <span>Profile: {act.target_profile_id.slice(0, 14)}…</span>
                                ) : (
                                  "—"
                                )}
                              </td>
                              <td className="py-3 px-4">
                                {act.status === "succeeded" && (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#dcfce7] text-[#15803d]">
                                    <CheckCircle2 size={12} /> Succeeded
                                  </span>
                                )}
                                {act.status === "claimed" && (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#e0f2fe] text-[#0369a1]">
                                    <Clock size={12} /> Claimed
                                  </span>
                                )}
                                {act.status === "needs_review" && (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#fef3c7] text-[#b45309]">
                                    <AlertCircle size={12} /> Needs Review
                                  </span>
                                )}
                                {act.status === "failed" && (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#fee2e2] text-[#b91c1c]">
                                    <XCircle size={12} /> Failed
                                  </span>
                                )}
                              </td>
                              <td className="py-3 px-4 text-[#475569] max-w-xs truncate">
                                {act.comment_text
                                  ? act.comment_text
                                  : act.error_message
                                  ? act.error_message
                                  : "Completed normally"}
                              </td>
                              <td className="py-3 px-4 text-[#64748b] text-[12px] whitespace-nowrap">
                                {new Date(act.created_at).toLocaleString()}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 5. LinkedIn Connect Panel Tab */}
            {tab === "linkedin" && (
              <LinkedInConnectPanel
                activeBrand={activeBrand}
                connectedAccount={connectedAccount}
                onAccountBound={async (updated) => {
                  setActiveBrand(updated);
                  await loadBrandData();
                }}
              />
            )}
          </div>
        </div>
      </main>

      {/* Add Persona Modal */}
      {showAddPersona && (
        <PersonaModal
          title="Define Target Persona"
          initialData={null}
          onClose={() => setShowAddPersona(false)}
          onSave={async (data) => {
            if (!activeBrand) return;
            const res = await personasApi.create({
              company_profile_id: activeBrand.id,
              label: data.label,
              search_keywords: data.search_keywords,
              max_profiles: data.max_profiles,
            });
            if (res.success && res.persona) {
              setPersonas((prev) => [...prev, res.persona!]);
              setShowAddPersona(false);
            }
          }}
        />
      )}

      {/* Edit Persona Modal */}
      {editingPersona && (
        <PersonaModal
          title={`Edit Persona: ${editingPersona.label}`}
          initialData={editingPersona}
          onClose={() => setEditingPersona(null)}
          onSave={async (data) => {
            if (!activeBrand) return;
            const res = await personasApi.update(editingPersona.id, data, activeBrand.id);
            if (res.success && res.persona) {
              setPersonas((prev) =>
                prev.map((p) => (p.id === editingPersona.id ? res.persona! : p))
              );
              setEditingPersona(null);
            }
          }}
        />
      )}
    </div>
  );
}

/* ── UI Components ───────────────────────────────────────────────────────── */

function TabBtn({
  label,
  count,
  active,
  onClick,
}: {
  label: string;
  count?: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`relative py-3 sm:py-3.5 text-[13.5px] font-medium transition-colors focus-visible:outline-none cursor-pointer whitespace-nowrap ${
        active ? "text-[#2f6fd6]" : "text-[#7a848c] hover:text-[#1f2a30]"
      }`}
    >
      {label}
      {count ? (
        <span className="ml-1.5 text-[11px] font-semibold text-[#5a6771] bg-[#eef1f4] rounded-full px-1.5 py-0.5">
          {count}
        </span>
      ) : null}
      {active && (
        <span className="absolute left-0 right-0 -bottom-px h-0.5 bg-[#2f6fd6] rounded-full" />
      )}
    </button>
  );
}

function Meter({
  label,
  value,
  max,
  icon,
}: {
  label: string;
  value: number;
  max?: number;
  icon?: React.ReactNode;
}) {
  const fallbackMax = label === "Likes" ? 15 : label === "Comments" ? 5 : 10;
  const safeMax = max && max > 0 ? max : fallbackMax;
  const safeVal = value ?? 0;
  const pct = Math.min(100, (safeVal / safeMax) * 100);
  return (
    <div className="flex items-center gap-2.5 min-w-[130px]">
      {icon}
      <div className="text-[12.5px]">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[#64748b]">{label}</span>
          <span className="font-semibold text-[#1f2a30] tabular-nums">
            {safeVal} / {safeMax}
          </span>
        </div>
        <div className="w-20 h-1.5 rounded-full bg-[#e2e8f0] overflow-hidden mt-1">
          <div
            className="h-full bg-[#2f6fd6] rounded-full transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  );
}

function ToggleSwitch({
  checked,
  disabled,
  onChange,
  activeColor = "bg-[#2f6fd6]",
}: {
  checked: boolean;
  disabled?: boolean;
  onChange: (next: boolean) => void;
  activeColor?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
        checked ? activeColor : "bg-[#cdd4d8]"
      } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      <span
        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
          checked ? "translate-x-5" : "translate-x-0"
        }`}
      />
    </button>
  );
}

function PersonaCard({
  persona,
  onEdit,
  onDelete,
}: {
  persona: TargetPersona;
  onEdit: (p: TargetPersona) => void;
  onDelete: (id: string) => void;
}) {
  const keywords = persona.search_keywords
    .split(/[,\s]+/)
    .map((k) => k.trim())
    .filter(Boolean);

  return (
    <div className="rounded-[14px] border border-[#e6e9ec] bg-white p-5 shadow-sm flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-[15px] font-semibold text-[#1f2a30]">{persona.label}</h3>
          <span
            className={`shrink-0 text-[11px] font-semibold rounded-full px-2 py-0.5 ${
              persona.is_active
                ? "bg-[#e7f4ec] text-[#1f8a5b]"
                : "bg-[#f0f1f3] text-[#7a848c]"
            }`}
          >
            {persona.is_active ? "Active" : "Paused"}
          </span>
        </div>

        <p className="text-[11px] font-semibold tracking-wider text-[#9aa4ac] uppercase mt-3 mb-2">
          Search Keywords
        </p>
        <div className="flex flex-wrap gap-1.5">
          {keywords.map((k, i) => (
            <span
              key={`${k}-${i}`}
              className="text-[12px] text-[#3a4750] bg-[#f2f4f6] border border-[#e6e9ec] rounded-md px-2 py-0.5"
            >
              {k}
            </span>
          ))}
        </div>

        <div className="flex items-center gap-2 text-[12.5px] text-[#5a6771] mt-4">
          <Target size={14} className="text-[#8a949c]" />
          Max {persona.max_profiles} candidate profiles
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-[#eef0f2] flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={() => onEdit(persona)}
          className="inline-flex items-center gap-1 text-[12.5px] font-medium text-[#475569] hover:text-[#1e293b] rounded-[7px] px-2.5 py-1.5 hover:bg-[#f1f5f9] transition-colors cursor-pointer"
        >
          <Edit2 size={13} /> Edit
        </button>
        <button
          type="button"
          onClick={() => onDelete(persona.id)}
          className="inline-flex items-center gap-1 text-[12.5px] font-medium text-[#b91c1c] hover:text-[#991b1b] rounded-[7px] px-2.5 py-1.5 hover:bg-[#fef2f2] transition-colors cursor-pointer"
        >
          <Trash2 size={13} /> Delete
        </button>
      </div>
    </div>
  );
}

function PersonaModal({
  title,
  initialData,
  onClose,
  onSave,
}: {
  title: string;
  initialData: TargetPersona | null;
  onClose: () => void;
  onSave: (data: {
    label: string;
    search_keywords: string;
    max_profiles: number;
    is_active?: boolean;
  }) => Promise<void>;
}) {
  const [label, setLabel] = useState(initialData?.label || "");
  const [keywords, setKeywords] = useState(initialData?.search_keywords || "");
  const [maxProfiles, setMaxProfiles] = useState(initialData?.max_profiles || 150);
  const [isActive, setIsActive] = useState(initialData?.is_active ?? true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!label.trim() || !keywords.trim()) {
      setError("Please fill in both label and keywords.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onSave({
        label: label.trim(),
        search_keywords: keywords.trim(),
        max_profiles: maxProfiles,
        is_active: isActive,
      });
    } catch (err: unknown) {
      setError((err as Error)?.message || "Failed to save persona.");
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-[#0d1a20]/40 flex items-center justify-center p-4 backdrop-blur-xs"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-[16px] bg-white shadow-xl p-6"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-[16px] font-semibold text-[#1f2a30]">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            className="w-7 h-7 grid place-items-center rounded-[7px] text-[#8a949c] hover:bg-[#f4f6f7] hover:text-[#1f2a30] cursor-pointer"
          >
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[13px] font-medium text-[#1f2a30] mb-1">
              Persona Label
            </label>
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="e.g. AI Founders & CTOs"
              className="w-full rounded-[8px] border border-[#dfe4e7] px-3 py-2 text-[13.5px] focus:outline-none focus:border-[#2f6fd6]"
            />
          </div>

          <div>
            <label className="block text-[13px] font-medium text-[#1f2a30] mb-1">
              LinkedIn Search Keywords
            </label>
            <input
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="e.g. founder CEO AI machine learning startup"
              className="w-full rounded-[8px] border border-[#dfe4e7] px-3 py-2 text-[13.5px] focus:outline-none focus:border-[#2f6fd6]"
            />
          </div>

          <div>
            <div className="flex items-center justify-between text-[13px] mb-1">
              <span className="font-medium text-[#1f2a30]">Max Target Profiles</span>
              <span className="font-bold text-[#2f6fd6]">{maxProfiles}</span>
            </div>
            <input
              type="range"
              min={10}
              max={500}
              step={10}
              value={maxProfiles}
              onChange={(e) => setMaxProfiles(Number(e.target.value))}
              className="w-full accent-[#2f6fd6] cursor-pointer"
            />
          </div>

          {initialData && (
            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="is_active_chk"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="w-4 h-4 accent-[#2f6fd6]"
              />
              <label htmlFor="is_active_chk" className="text-[13px] text-[#475569]">
                Active (eligible for background targeting)
              </label>
            </div>
          )}

          {error && <p className="text-[12.5px] text-[#b91c1c]">{error}</p>}

          <div className="flex justify-end gap-2 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-[8px] border border-[#dfe4e7] bg-white text-[#5a6771] text-[13px] font-medium px-4 py-2 hover:bg-[#f4f6f7] cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-[8px] bg-[#2f6fd6] hover:bg-[#255cc0] text-white text-[13px] font-semibold px-4 py-2 disabled:opacity-50 cursor-pointer"
            >
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
              Save Persona
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

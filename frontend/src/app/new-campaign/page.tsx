"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  ChatMessage,
  CampaignStreamEvent,
} from "@/components/campaign/types";
import { useAuth } from "@/context/AuthContext";
import {
  streamCampaignResponse,
  createCampaignSession,
  CampaignSession,
} from "@/components/campaign/apiAdapter";
import Sidebar from "@/components/shell/Sidebar";
import CampaignBrief from "@/components/campaign/CampaignBrief";
import type { IntakeChecklistState, CampaignPlanDocument } from "@/lib/api";
import { ChevronLeft, ArrowUp, Check, Sparkles, Loader2 } from "lucide-react";

type TabKey = "chat" | "content" | "calendar" | "strategy";

const TABS: { key: TabKey; label: string }[] = [
  { key: "chat", label: "Chat" },
  { key: "content", label: "Content" },
  { key: "calendar", label: "Calendar" },
  { key: "strategy", label: "Strategy brief" },
];

interface BriefSnapshot {
  checklist: IntakeChecklistState | null;
  plan: CampaignPlanDocument | null;
  intakeComplete: boolean;
  generated: boolean;
}

interface GeneratedPost {
  id: string;
  content: string;
  scheduledAt?: string;
  mediaType?: string;
}

export default function CampaignWorkspacePage() {
  const { user, setIsAuthModalOpen } = useAuth();
  const router = useRouter();

  const sessionRef = useRef<CampaignSession | null>(null);
  const hasRedirectedRef = useRef(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [tab, setTab] = useState<TabKey>("chat");
  const [savedFlash, setSavedFlash] = useState(false);
  const [posts, setPosts] = useState<GeneratedPost[]>([]);

  const [brief, setBrief] = useState<BriefSnapshot>({
    checklist: null,
    plan: null,
    intakeComplete: false,
    generated: false,
  });

  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isGenerating]);

  const syncBrief = () => {
    const s = sessionRef.current;
    if (!s) return;
    setBrief({
      checklist: s.checklist ?? null,
      plan: s.plan ?? null,
      intakeComplete: s.intakeComplete,
      generated: s.generated,
    });
  };

  const handleSendMessage = async (promptText: string) => {
    if (isGenerating) return;
    if (!user) {
      setIsAuthModalOpen(true);
      return;
    }
    if (sessionRef.current?.userId !== user.id) {
      sessionRef.current = createCampaignSession(user.id);
    }

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
      thoughts: [],
      isThinking: true,
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setIsGenerating(true);

    try {
      await streamCampaignResponse(
        promptText,
        (event: CampaignStreamEvent) => {
          switch (event.type) {
            case "thought":
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, thoughts: [...(m.thoughts || []), event.step] }
                    : m
                )
              );
              break;
            case "content":
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, isThinking: false, content: m.content + event.chunk }
                    : m
                )
              );
              break;
            case "artifact_post_add":
              setPosts((prev) => {
                const next = [
                  ...prev.filter((p) => p.id !== event.post.id),
                  {
                    id: event.post.id,
                    content: event.post.content,
                    scheduledAt: event.post.scheduledAt,
                    mediaType: event.post.mediaType,
                  },
                ];
                return next;
              });
              break;
            case "artifact_posts_set":
              setPosts(
                event.posts.map((p) => ({
                  id: p.id,
                  content: p.content,
                  scheduledAt: p.scheduledAt,
                  mediaType: p.mediaType,
                }))
              );
              break;
            case "done":
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, isThinking: false, isStreaming: false }
                    : m
                )
              );
              setIsGenerating(false);
              {
                const targetCampaignId = sessionRef.current?.campaignId;
                if (targetCampaignId && !hasRedirectedRef.current) {
                  hasRedirectedRef.current = true;
                  router.push(`/campaigns/${targetCampaignId}`);
                }
              }
              break;
          }
        },
        sessionRef.current
      );
    } catch {
      setIsGenerating(false);
    } finally {
      syncBrief();
    }
  };

  const handleGenerate = () => handleSendMessage("Generate the campaign now.");

  const handleSaveDraft = () => {
    // Intake and campaign state are persisted server-side on every turn, so this
    // confirms that saved state rather than issuing a separate write.
    setSavedFlash(true);
    setTimeout(() => setSavedFlash(false), 1600);
  };

  const campaignName = (brief.checklist?.campaign_name || "").trim() || "Untitled campaign";
  const isInitial = messages.length === 0;
  const showReadyCard = brief.intakeComplete && !brief.generated && !isGenerating;

  return (
    <div className="flex h-screen bg-[#f6f7f8] text-[#1f2a30] overflow-hidden">
      <Sidebar active="campaigns" />

      {/* Center column */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 shrink-0 border-b border-[#e6e9ec] bg-white flex items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-2 min-w-0">
            <button
              type="button"
              onClick={() => router.back()}
              className="inline-flex items-center gap-1 text-[13px] text-[#5a6771] hover:text-[#1f2a30] rounded px-1.5 py-1 hover:bg-[#f4f6f7] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#137082]/30"
            >
              <ChevronLeft size={15} /> Campaigns
            </button>
            <span className="text-[#c8ced2]">/</span>
            <span className="text-[14px] font-semibold text-[#1f2a30] truncate">
              {campaignName}
            </span>
            <span className="ml-1 text-[10.5px] font-semibold uppercase tracking-wide text-[#8a949c] border border-[#e6e9ec] rounded px-1.5 py-0.5">
              {brief.generated ? "Generated" : "Draft"}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleSaveDraft}
              className="inline-flex items-center gap-1.5 text-[13px] font-medium text-[#5a6771] hover:text-[#1f2a30] border border-[#e0e4e7] rounded-[8px] px-3 py-1.5 hover:bg-[#f4f6f7] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#137082]/30"
            >
              {savedFlash ? (
                <>
                  <Check size={14} className="text-[#3a8f6b]" /> Saved
                </>
              ) : (
                "Save draft"
              )}
            </button>
            <button
              type="button"
              onClick={() => router.push("/")}
              className="text-[13px] font-medium text-[#5a6771] hover:text-[#1f2a30] rounded-[8px] px-3 py-1.5 hover:bg-[#f4f6f7] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#137082]/30"
            >
              Exit
            </button>
          </div>
        </header>

        {/* Tabs */}
        <div className="shrink-0 border-b border-[#e6e9ec] bg-white px-4 sm:px-6">
          <div className="flex gap-6" role="tablist" aria-label="Campaign sections">
            {TABS.map((t) => (
              <button
                key={t.key}
                role="tab"
                aria-selected={tab === t.key}
                onClick={() => setTab(t.key)}
                className={`relative py-3 text-[13.5px] font-medium transition-colors focus-visible:outline-none ${
                  tab === t.key
                    ? "text-[#116677]"
                    : "text-[#7a848c] hover:text-[#1f2a30]"
                }`}
              >
                {t.label}
                {tab === t.key && (
                  <span className="absolute left-0 right-0 -bottom-px h-0.5 bg-[#137082] rounded-full" />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Tab body + brief */}
        <div className="flex-1 flex min-h-0">
          <div className="flex-1 flex flex-col min-w-0">
            {tab === "chat" && (
              <>
                <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 sm:px-8 py-6">
                  <div className="max-w-2xl mx-auto">
                    {isInitial ? (
                      <div className="pt-10 text-center">
                        <h1 className="text-[22px] font-semibold text-[#1f2a30]">
                          Let&apos;s build your campaign
                        </h1>
                        <p className="text-[14px] text-[#7a848c] mt-2 max-w-md mx-auto">
                          Tell your campaign strategist what you want to promote and who it is
                          for. We&apos;ll shape the brief together.
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-6">
                        {messages.map((m) =>
                          m.role === "user" ? (
                            <div key={m.id}>
                              <p className="text-[11px] font-semibold uppercase tracking-wide text-[#9aa4ac] mb-1.5">
                                You
                              </p>
                              <div className="rounded-[12px] bg-[#eaf3f5] border border-[#d5e7ea] px-4 py-3 text-[14px] leading-relaxed text-[#26333b] whitespace-pre-wrap">
                                {m.content}
                              </div>
                            </div>
                          ) : (
                            <div key={m.id}>
                              <p className="text-[11px] font-semibold uppercase tracking-wide text-[#116677] mb-1.5">
                                Campaign strategist
                              </p>
                              {m.isThinking && !m.content ? (
                                <p className="text-[14px] text-[#9aa4ac] flex items-center gap-2">
                                  <Loader2 size={14} className="animate-spin" /> Thinking…
                                </p>
                              ) : (
                                <div className="text-[14px] leading-relaxed text-[#374751] whitespace-pre-wrap">
                                  {m.content}
                                </div>
                              )}
                            </div>
                          )
                        )}

                        {showReadyCard && (
                          <div className="rounded-[12px] border border-[#d5e7ea] bg-white px-4 py-4 flex items-center justify-between gap-4 shadow-sm">
                            <div>
                              <p className="text-[14px] font-semibold text-[#1f2a30]">
                                Campaign ready
                              </p>
                              <p className="text-[12.5px] text-[#7a848c] mt-0.5">
                                You can still refine the brief before generating.
                              </p>
                            </div>
                            <button
                              type="button"
                              onClick={handleGenerate}
                              className="shrink-0 inline-flex items-center gap-2 rounded-[9px] bg-[#137082] hover:bg-[#0f5b6a] text-white text-[13.5px] font-semibold px-4 py-2.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#137082]/40"
                            >
                              <Sparkles size={15} /> Generate campaign
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Composer */}
                <div className="shrink-0 border-t border-[#e6e9ec] bg-white px-4 sm:px-8 py-3">
                  <Composer onSend={handleSendMessage} disabled={isGenerating} />
                </div>
              </>
            )}

            {tab === "content" && (
              <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6">
                <div className="max-w-2xl mx-auto">
                  {posts.length === 0 ? (
                    <EmptyTab
                      title="No content yet"
                      body="Generated LinkedIn posts will appear here once you generate the campaign."
                    />
                  ) : (
                    <div className="space-y-4">
                      {posts.map((p, i) => (
                        <div
                          key={p.id}
                          className="rounded-[12px] border border-[#e6e9ec] bg-white p-4 shadow-sm"
                        >
                          <p className="text-[11px] font-semibold uppercase tracking-wide text-[#9aa4ac] mb-2">
                            Post {i + 1}
                            {p.mediaType === "video" ? " · Video" : ""}
                          </p>
                          <p className="text-[13.5px] leading-relaxed text-[#26333b] whitespace-pre-wrap">
                            {p.content}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {tab === "calendar" && (
              <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6">
                <div className="max-w-2xl mx-auto">
                  <EmptyTab
                    title="Schedule coming up"
                    body="Your posting schedule will show here after the campaign is generated."
                  />
                </div>
              </div>
            )}

            {tab === "strategy" && (
              <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6">
                <div className="max-w-2xl mx-auto">
                  <EmptyTab
                    title="Strategy brief"
                    body="The full strategy brief will appear here. Tell me what you want in this tab and I'll build it."
                  />
                </div>
              </div>
            )}
          </div>

          {/* Right brief panel — only on the Chat tab */}
          {tab === "chat" && (
            <CampaignBrief
              checklist={brief.checklist}
              plan={brief.plan}
              generated={brief.generated}
            />
          )}
        </div>
      </main>
    </div>
  );
}

/* ── Composer ─────────────────────────────────────────────────────────── */

function Composer({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void;
  disabled: boolean;
}) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (ref.current) {
      ref.current.style.height = "auto";
      ref.current.style.height = `${Math.min(ref.current.scrollHeight, 140)}px`;
    }
  }, [text]);

  const submit = () => {
    const t = text.trim();
    if (!t || disabled) return;
    onSend(t);
    setText("");
    if (ref.current) ref.current.style.height = "auto";
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="rounded-[14px] border border-[#dfe4e7] bg-white focus-within:border-[#137082] focus-within:ring-2 focus-within:ring-[#137082]/15 transition-colors px-3.5 py-2.5">
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
          className="w-full bg-transparent text-[14px] text-[#1f2a30] placeholder-[#9aa4ac] focus:outline-none resize-none leading-relaxed max-h-36"
        />
        <div className="flex items-center justify-end pt-1.5">
          <button
            type="button"
            onClick={submit}
            disabled={!text.trim() || disabled}
            aria-label="Send message"
            className={`inline-flex items-center gap-1.5 rounded-[8px] px-3.5 py-1.5 text-[13px] font-semibold transition-colors ${
              text.trim() && !disabled
                ? "bg-[#137082] text-white hover:bg-[#0f5b6a]"
                : "bg-[#eef1f2] text-[#a6afb5] cursor-not-allowed"
            }`}
          >
            Send <ArrowUp size={14} strokeWidth={2.5} />
          </button>
        </div>
      </div>
      <p className="text-[11px] text-[#a6afb5] text-center mt-1.5">
        Shift + Return for a new line
      </p>
    </div>
  );
}

/* ── Empty tab state ──────────────────────────────────────────────────── */

function EmptyTab({ title, body }: { title: string; body: string }) {
  return (
    <div className="pt-16 text-center">
      <h2 className="text-[16px] font-semibold text-[#1f2a30]">{title}</h2>
      <p className="text-[13.5px] text-[#7a848c] mt-1.5 max-w-sm mx-auto">{body}</p>
    </div>
  );
}

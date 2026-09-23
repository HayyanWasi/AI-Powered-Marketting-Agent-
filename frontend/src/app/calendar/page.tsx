"use client";

import { useState, useEffect, useCallback } from "react";
import Sidebar from "@/components/shell/Sidebar";
import { campaignApi, autopilotApi } from "@/lib/api";
import { Play, FileText, MoreHorizontal, Loader2, CalendarClock } from "lucide-react";

interface SchedPost {
  id: string;
  campaignId: string;
  campaignName: string;
  title: string;
  scheduledAt: string;
  status: string;
  isVideo: boolean;
}

const STATUS_META: Record<string, { label: string; cls: string }> = {
  draft: { label: "Draft", cls: "bg-[#f0f1f3] text-[#7a848c]" },
  scheduled: { label: "Scheduled", cls: "bg-[#e8eefc] text-[#1f5fbf]" },
  publishing: { label: "Publishing", cls: "bg-[#e6f2f4] text-[#137082]" },
  published: { label: "Published", cls: "bg-[#e7f4ec] text-[#1f8a5b]" },
  failed: { label: "Failed", cls: "bg-[#fbecea] text-[#b3392b]" },
  needs_review: { label: "Needs review", cls: "bg-[#fdf3e3] text-[#9a6212]" },
};

const FILTERS = [
  { key: "all", label: "All statuses" },
  { key: "scheduled", label: "Scheduled" },
  { key: "needs_review", label: "Needs review" },
  { key: "draft", label: "Draft" },
  { key: "published", label: "Published" },
  { key: "failed", label: "Failed" },
];

function startOfDay(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}
function dayLabel(dateKey: number): string {
  const today = startOfDay(new Date());
  const oneDay = 86400000;
  const d = new Date(dateKey);
  const fmt = d.toLocaleDateString([], { weekday: "short", day: "numeric", month: "short" });
  if (dateKey === today) return `Today, ${fmt}`;
  if (dateKey === today + oneDay) return `Tomorrow, ${fmt}`;
  return fmt;
}
function timeLabel(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
function tzLabel(): string {
  const offMin = -new Date().getTimezoneOffset();
  const sign = offMin >= 0 ? "+" : "-";
  const h = Math.floor(Math.abs(offMin) / 60);
  return `All times in your local time (UTC${sign}${h})`;
}

export default function CalendarPage() {
  const [posts, setPosts] = useState<SchedPost[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [filter, setFilter] = useState("all");

  const load = useCallback(async () => {
    setState("loading");
    try {
      const list = await campaignApi.list({ page_size: 100 });
      const chunks = await Promise.all(
        list.campaigns.map(async (c) => {
          try {
            const rows = await campaignApi.getPosts(c.id);
            return rows
              .filter((p) => p.scheduled_at)
              .map<SchedPost>((p) => ({
                id: p.id,
                campaignId: c.id,
                campaignName: c.name,
                title:
                  (p.hook || p.full_content || "LinkedIn post")
                    .split("\n")[0]
                    .slice(0, 90) || "LinkedIn post",
                scheduledAt: p.scheduled_at as string,
                status: (p.status || "draft").toLowerCase(),
                isVideo: p.media_type === "video",
              }));
          } catch {
            return [];
          }
        })
      );
      setPosts(chunks.flat());
      setState("ready");
    } catch {
      setState("error");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleRemove = async (id: string) => {
    setPosts((prev) => prev.filter((p) => p.id !== id));
    try {
      await autopilotApi.deleteQueueItem(id);
    } catch {
      load();
    }
  };
  const handlePublishNow = async (id: string) => {
    try {
      await autopilotApi.publishNow(id);
      setPosts((prev) =>
        prev.map((p) => (p.id === id ? { ...p, status: "published" } : p))
      );
    } catch {
      /* leave as-is on failure */
    }
  };

  const visible = filter === "all" ? posts : posts.filter((p) => p.status === filter);

  // Group by calendar day; upcoming days ascending, past days after (descending).
  const groups = (() => {
    const map = new Map<number, SchedPost[]>();
    for (const p of visible) {
      const key = startOfDay(new Date(p.scheduledAt));
      const arr = map.get(key) ?? [];
      arr.push(p);
      map.set(key, arr);
    }
    const today = startOfDay(new Date());
    const keys = [...map.keys()];
    const upcoming = keys.filter((k) => k >= today).sort((a, b) => a - b);
    const past = keys.filter((k) => k < today).sort((a, b) => b - a);
    return [...upcoming, ...past].map((k) => ({
      key: k,
      isPast: k < today,
      items: (map.get(k) ?? []).sort(
        (a, b) => Date.parse(a.scheduledAt) - Date.parse(b.scheduledAt)
      ),
    }));
  })();

  const queuedThisWeek = posts.filter(
    (p) => p.status === "scheduled" || p.status === "publishing"
  ).length;

  return (
    <div className="flex h-screen bg-[#f6f7f8] text-[#1f2a30] overflow-hidden font-sans">
      <Sidebar active="calendar" />

      <main className="flex-1 flex flex-col min-w-0">
        {/* Top bar (title is sans, consistent with the rest of the app) */}
        <header className="h-14 shrink-0 border-b border-[#e6e9ec] bg-white flex items-center justify-between px-4 sm:px-6">
          <div className="min-w-0 flex items-baseline gap-2.5">
            <h1 className="text-[18px] font-semibold text-[#1f2a30]">Schedule</h1>
            <p className="text-[13px] text-[#8a949c] truncate hidden sm:block">
              Everything queued to go out
            </p>
          </div>
          <label className="flex items-center gap-2 text-[13px] text-[#5a6771]">
            <span className="sr-only">Filter by status</span>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="rounded-[8px] border border-[#dfe4e7] bg-white px-2.5 py-1.5 text-[13px] text-[#1f2a30] focus:outline-none focus:border-[#2f6fd6] focus:ring-2 focus:ring-[#2f6fd6]/15"
            >
              {FILTERS.map((f) => (
                <option key={f.key} value={f.key}>
                  {f.label}
                </option>
              ))}
            </select>
          </label>
        </header>

        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 py-5">
            {/* Meta row */}
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2 text-[12.5px] text-[#5a6771]">
                <span className="w-2 h-2 rounded-full bg-[#1f8a5b]" />
                <span className="font-medium text-[#1f2a30]">{queuedThisWeek} queued</span>
                <span className="text-[#c8ced2]">·</span>
                <span>Automated dispatch active</span>
              </div>
              <span className="text-[12px] text-[#9aa4ac] hidden sm:block">{tzLabel()}</span>
            </div>

            {state === "loading" && (
              <div className="space-y-3">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="h-16 rounded-[12px] bg-white border border-[#eef0f2] animate-pulse" />
                ))}
              </div>
            )}

            {state === "error" && (
              <div className="pt-16 text-center">
                <h2 className="text-[16px] font-semibold text-[#1f2a30]">
                  We couldn&apos;t load your schedule
                </h2>
                <button
                  type="button"
                  onClick={load}
                  className="mt-3 inline-flex items-center rounded-[8px] border border-[#dfe4e7] bg-white text-[#1f2a30] text-[13px] font-medium px-3.5 py-2 hover:bg-[#f4f6f7]"
                >
                  Try again
                </button>
              </div>
            )}

            {state === "ready" && groups.length === 0 && (
              <div className="pt-16 text-center">
                <div className="w-11 h-11 rounded-full bg-[#eef1f4] grid place-items-center mx-auto mb-3 text-[#8a949c]">
                  <CalendarClock size={20} />
                </div>
                <h2 className="text-[16px] font-semibold text-[#1f2a30]">Nothing scheduled yet</h2>
                <p className="text-[13.5px] text-[#7a848c] mt-1.5 max-w-sm mx-auto">
                  Posts and videos you schedule from a campaign will appear here, soonest first.
                </p>
              </div>
            )}

            {state === "ready" && groups.length > 0 && (
              <div className="space-y-6">
                {groups.map((g) => (
                  <section key={g.key}>
                    {/* Consistent day header (sans, same style for every group) */}
                    <div className="flex items-center justify-between mb-2.5">
                      <h2 className="text-[13.5px] font-semibold text-[#1f2a30]">
                        {dayLabel(g.key)}
                      </h2>
                      <span className="text-[12px] text-[#9aa4ac]">
                        {g.items.length} {g.items.length === 1 ? "item" : "items"}
                      </span>
                    </div>

                    {/* Consistent card container for every day */}
                    <div className="rounded-[12px] border border-[#e6e9ec] bg-white overflow-hidden divide-y divide-[#eef0f2] shadow-sm">
                      {g.items.map((p) => (
                        <Row
                          key={p.id}
                          post={p}
                          dimmed={g.isPast}
                          onRemove={() => handleRemove(p.id)}
                          onPublishNow={() => handlePublishNow(p.id)}
                        />
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function Row({
  post,
  dimmed,
  onRemove,
  onPublishNow,
}: {
  post: SchedPost;
  dimmed: boolean;
  onRemove: () => void;
  onPublishNow: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const meta = STATUS_META[post.status] ?? STATUS_META.draft;
  const canPublish = post.status === "scheduled" || post.status === "draft";

  return (
    <div className={`flex items-center gap-3 px-4 py-3.5 ${dimmed ? "opacity-70" : ""}`}>
      {/* Time (prominent, tabular) */}
      <span className="text-[14px] font-semibold text-[#1f2a30] tabular-nums w-[76px] shrink-0">
        {timeLabel(post.scheduledAt)}
      </span>

      {/* Type icon */}
      <span
        className="w-7 h-7 rounded-md bg-[#f2f4f6] grid place-items-center text-[#5a6771] shrink-0"
        title={post.isVideo ? "Video" : "Post"}
      >
        {post.isVideo ? <Play size={13} className="fill-current" /> : <FileText size={14} />}
      </span>

      {/* Title + campaign */}
      <div className="min-w-0 flex-1">
        <p className="text-[13.5px] font-medium text-[#1f2a30] truncate">{post.title}</p>
        <p className="text-[12px] text-[#8a949c] truncate">
          {post.campaignName} · LinkedIn
        </p>
      </div>

      {/* Status */}
      <span className={`shrink-0 text-[11px] font-semibold rounded-full px-2 py-0.5 ${meta.cls}`}>
        {meta.label}
      </span>

      {/* Row menu */}
      <div className="relative shrink-0">
        <button
          type="button"
          onClick={() => setMenuOpen((v) => !v)}
          aria-label="Post actions"
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          className="w-7 h-7 grid place-items-center rounded-[7px] text-[#9aa4ac] hover:bg-[#f2f4f6] hover:text-[#1f2a30]"
        >
          <MoreHorizontal size={16} />
        </button>
        {menuOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
            <div
              role="menu"
              className="absolute right-0 top-8 z-20 w-40 rounded-[10px] border border-[#e6e9ec] bg-white shadow-lg py-1"
            >
              {canPublish && (
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setMenuOpen(false);
                    onPublishNow();
                  }}
                  className="w-full text-left px-3 py-2 text-[13px] text-[#1f2a30] hover:bg-[#f4f6f7]"
                >
                  Publish now
                </button>
              )}
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false);
                  onRemove();
                }}
                className="w-full text-left px-3 py-2 text-[13px] text-[#b3392b] hover:bg-[#fbece9]"
              >
                Remove
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

"use client";

import { useState, useEffect, useCallback } from "react";
import {
  MessageSquare, CheckCircle2, XCircle, RefreshCw, Loader2,
  Clock, ChevronDown, ChevronUp, CheckCheck
} from "lucide-react";
import { reviewQueueApi, ReviewComment } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  pending_review: "text-amber-400 bg-amber-400/10 border-amber-400/20",
  approved: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
  rejected: "text-rose-400 bg-rose-400/10 border-rose-400/20",
  published: "text-blue-400 bg-blue-400/10 border-blue-400/20",
  expired: "text-zinc-500 bg-zinc-500/10 border-zinc-500/20",
};

const STATUS_LABELS: Record<string, string> = {
  pending_review: "Pending Review",
  approved: "Approved",
  rejected: "Rejected",
  published: "Published",
  expired: "Expired",
};

export default function ReviewQueueCard() {
  const [comments, setComments] = useState<ReviewComment[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"pending_review" | "all">("pending_review");
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [approvingAll, setApprovingAll] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const loadComments = useCallback(async () => {
    setLoading(true);
    try {
      const res = await reviewQueueApi.list(filter);
      setComments(res.comments);
    } catch (e) {
      console.warn("Could not load review queue:", e);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { loadComments(); }, [loadComments]);

  const handleApprove = async (id: string) => {
    setApprovingId(id);
    try {
      await reviewQueueApi.approve(id);
      setComments((prev) =>
        prev.map((c) => c.id === id ? { ...c, status: "approved" as const } : c)
          .filter((c) => filter === "pending_review" ? c.status !== "approved" : true)
      );
    } catch (e) {
      console.warn("Approve failed:", e);
    } finally {
      setApprovingId(null);
    }
  };

  const handleReject = async (id: string) => {
    setRejectingId(id);
    try {
      await reviewQueueApi.reject(id);
      setComments((prev) =>
        prev.map((c) => c.id === id ? { ...c, status: "rejected" as const } : c)
          .filter((c) => filter === "pending_review" ? c.status !== "rejected" : true)
      );
    } catch (e) {
      console.warn("Reject failed:", e);
    } finally {
      setRejectingId(null);
    }
  };

  const handleApproveAll = async () => {
    setApprovingAll(true);
    try {
      const res = await reviewQueueApi.approveAll();
      if (res.success) {
        setComments([]);
      }
    } catch (e) {
      console.warn("Approve all failed:", e);
    } finally {
      setApprovingAll(false);
    }
  };

  const pendingCount = comments.filter((c) => c.status === "pending_review").length;

  return (
    <div className="bg-[#151C25] border border-zinc-800/60 rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800/60">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-amber-500/15 flex items-center justify-center">
            <MessageSquare size={14} className="text-amber-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="text-sm font-semibold text-zinc-100">Comment Review Queue</p>
              {pendingCount > 0 && (
                <span className="px-1.5 py-0.5 rounded-full bg-amber-500 text-[10px] font-bold text-zinc-950">
                  {pendingCount}
                </span>
              )}
            </div>
            <p className="text-[10px] text-zinc-500">Approve AI-generated comments before publishing</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {pendingCount > 0 && (
            <button
              onClick={handleApproveAll}
              disabled={approvingAll}
              className="flex items-center gap-1.5 h-7 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white text-xs font-medium transition-all"
            >
              {approvingAll ? <Loader2 size={11} className="animate-spin" /> : <CheckCheck size={11} />}
              Approve All
            </button>
          )}
          <button
            onClick={loadComments}
            className="w-7 h-7 rounded-lg bg-zinc-800 hover:bg-zinc-700 flex items-center justify-center text-zinc-400 transition-all"
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex border-b border-zinc-800/60">
        {(["pending_review", "all"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`flex-1 py-2 text-[11px] font-medium transition-colors ${filter === f
                ? "text-zinc-100 border-b-2 border-amber-500"
                : "text-zinc-500 hover:text-zinc-300"
              }`}
          >
            {f === "pending_review" ? "Pending Review" : "All Comments"}
          </button>
        ))}
      </div>

      {/* List */}
      <div className="divide-y divide-zinc-800/40 max-h-[420px] overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-10 gap-2 text-zinc-600 text-xs">
            <Loader2 size={14} className="animate-spin" />
            Loading…
          </div>
        ) : comments.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 gap-2 text-center px-5">
            <CheckCircle2 size={22} className="text-emerald-500/40" />
            <p className="text-xs text-zinc-500">
              {filter === "pending_review" ? "No comments pending review" : "No comments found"}
            </p>
            <p className="text-[11px] text-zinc-600 max-w-xs">
              {filter === "pending_review"
                ? "AI will generate comments during engagement sessions. They'll appear here for approval."
                : "Comments will appear once the AI starts engagement sessions."}
            </p>
          </div>
        ) : (
          comments.map((c) => (
            <div key={c.id} className="px-5 py-3.5 hover:bg-zinc-800/20 transition-colors">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  {/* Meta */}
                  <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full border ${STATUS_COLORS[c.status] || STATUS_COLORS.expired}`}>
                      {STATUS_LABELS[c.status] || c.status}
                    </span>
                    <span className="text-[10px] text-zinc-600 flex items-center gap-1">
                      <Clock size={9} />
                      {new Date(c.generated_at).toLocaleString("en-PK", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                    </span>
                    {c.persona_label && (
                      <span className="text-[10px] text-violet-400">@{c.persona_label}</span>
                    )}
                  </div>
                  {/* Target post snippet */}
                  <p className="text-[10px] text-zinc-500 mb-1.5 italic">
                    On: "{c.target_post_snippet?.slice(0, 80) || "LinkedIn post"}…"
                  </p>
                  {/* Generated comment */}
                  <p className="text-xs text-zinc-300 leading-relaxed">
                    {expandedId === c.id
                      ? c.generated_text
                      : c.generated_text?.slice(0, 120) + (c.generated_text?.length > 120 ? "…" : "")}
                  </p>
                  {c.generated_text?.length > 120 && (
                    <button
                      onClick={() => setExpandedId(expandedId === c.id ? null : c.id)}
                      className="flex items-center gap-1 text-[10px] text-zinc-500 hover:text-zinc-300 mt-1 transition-colors"
                    >
                      {expandedId === c.id ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
                      {expandedId === c.id ? "Show less" : "Show more"}
                    </button>
                  )}
                  {c.reject_reason && (
                    <p className="text-[10px] text-rose-400 mt-1">Rejected: {c.reject_reason}</p>
                  )}
                </div>

                {/* Actions — only for pending */}
                {c.status === "pending_review" && (
                  <div className="flex items-center gap-1.5 shrink-0 pt-0.5">
                    <button
                      onClick={() => handleApprove(c.id)}
                      disabled={approvingId === c.id}
                      title="Approve"
                      className="w-7 h-7 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 flex items-center justify-center text-emerald-400 transition-all disabled:opacity-40"
                    >
                      {approvingId === c.id ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={13} />}
                    </button>
                    <button
                      onClick={() => handleReject(c.id)}
                      disabled={rejectingId === c.id}
                      title="Reject"
                      className="w-7 h-7 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 flex items-center justify-center text-rose-400 transition-all disabled:opacity-40"
                    >
                      {rejectingId === c.id ? <Loader2 size={12} className="animate-spin" /> : <XCircle size={13} />}
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

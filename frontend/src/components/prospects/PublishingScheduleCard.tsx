"use client";

import { useSyncExternalStore } from "react";
import {
  Calendar,
  Film,
  FileText,
  Sparkles,
  BrainCircuit,
  Zap,
  Clock,
  Trash2,
} from "lucide-react";
import { AutopilotSettings, QueueItem } from "./types";

interface Props {
  settings?: AutopilotSettings;
  queue: QueueItem[];
  onChangeSlot?: (
    slotKey: "post_time_slot" | "video_time_slot",
    value: string
  ) => void;
  onDeleteJob?: (id: string) => void;
}

export default function PublishingScheduleCard({
  settings,
  queue,
  onDeleteJob,
}: Props) {
  const timezoneLabel = useSyncExternalStore(
    () => () => {},
    () => {
      try {
        return (
          new Intl.DateTimeFormat("en-US", { timeZoneName: "short" })
            .formatToParts(new Date())
            .find((part) => part.type === "timeZoneName")?.value ||
          Intl.DateTimeFormat().resolvedOptions().timeZone ||
          "Local Time"
        );
      } catch {
        return "Local Time";
      }
    },
    () => "Local Time"
  );

  const getJobIcon = (type: QueueItem["type"]) => {
    switch (type) {
      case "video":
        return <Film size={14} className="text-purple-400" />;
      case "post":
      default:
        return <FileText size={14} className="text-blue-400" />;
    }
  };

  const getStatusBadge = (status: QueueItem["status"]) => {
    switch (status) {
      case "ready":
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            Ready
          </span>
        );
      case "uploading":
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse">
            Uploading...
          </span>
        );
      case "pending":
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-zinc-800 text-zinc-400 border border-zinc-700">
            Queued
          </span>
        );
    }
  };

  // Only display Feed Posts and Videos in the upcoming queue
  const displayQueue = queue.filter(
    (item) => item.type === "video" || item.type === "post"
  );

  // AI Calculated Optimal Windows (Defaults or from settings)
  const morningSlot = settings?.post_time_slot || "10:00 AM";
  const afternoonSlot = settings?.video_time_slot || "04:00 PM";

  return (
    <div className="rounded-xl bg-zinc-900/60 border border-zinc-800 p-6 flex flex-col justify-between shadow-lg backdrop-blur-sm">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-zinc-800 mb-6">
          <div>
            <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
              Publishing Schedule & Upcoming Queue
            </h2>
            <p className="text-xs text-zinc-400 mt-1">
              Autonomous dispatch engine with dynamic AI timing optimization.
            </p>
          </div>

          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-medium">
            <Sparkles size={13} />
            <span>AI Timing Sync</span>
          </div>
        </div>

        {/* 1. AI Smart-Scheduling: Active Status Card */}
        <div className="rounded-lg bg-zinc-950/80 border border-blue-500/20 p-4 mb-6 relative overflow-hidden">
          {/* Subtle background glow */}
          <div className="absolute top-0 right-0 w-48 h-48 bg-blue-500/5 blur-3xl rounded-full pointer-events-none -z-10" />

          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start space-x-3">
              <div className="w-9 h-9 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <BrainCircuit size={18} className="text-blue-400" />
              </div>

              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-semibold text-zinc-100 tracking-tight">
                    AI Smart-Scheduling: Active
                  </span>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse mr-1" />
                    AUTONOMOUS
                  </span>
                </div>
                <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                  The engine automatically calculates optimal B2B engagement windows based on follower activity analytics and global network density.
                </p>
              </div>
            </div>
          </div>

          {/* AI Calculated Windows Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4 pt-3 border-t border-zinc-800/80">
            {/* Morning Window */}
            <div className="p-3 rounded-lg bg-zinc-900/80 border border-zinc-800 flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <FileText size={14} className="text-blue-400 flex-shrink-0" />
                <div>
                  <span className="text-[11px] text-zinc-400 block">
                    Optimal Feed Post Window
                  </span>
                  <span className="text-xs font-semibold text-zinc-100 font-mono">
                    {morningSlot} <span className="text-[11px] text-zinc-400 font-sans font-normal">({timezoneLabel})</span>
                  </span>
                </div>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                Peak Morning
              </span>
            </div>

            {/* Afternoon Window */}
            <div className="p-3 rounded-lg bg-zinc-900/80 border border-zinc-800 flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <Film size={14} className="text-purple-400 flex-shrink-0" />
                <div>
                  <span className="text-[11px] text-zinc-400 block">
                    Optimal Video Broadcast Window
                  </span>
                  <span className="text-xs font-semibold text-zinc-100 font-mono">
                    {afternoonSlot} <span className="text-[11px] text-zinc-400 font-sans font-normal">({timezoneLabel})</span>
                  </span>
                </div>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
                Peak Afternoon
              </span>
            </div>
          </div>
        </div>

        {/* 2. Upcoming Queue List */}
        <div className="rounded-lg bg-zinc-950/70 border border-zinc-800/80 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-200 flex items-center space-x-2">
              <Calendar size={14} className="text-blue-400" />
              <span>Upcoming Queue (AI-Scheduled)</span>
            </span>
            <span className="text-[11px] font-mono text-zinc-500 flex items-center space-x-1">
              <Zap size={11} className="text-emerald-400" />
              <span>{displayQueue.length} jobs ready</span>
            </span>
          </div>

          <div className="divide-y divide-zinc-800/60 space-y-2.5 pt-1 max-h-[380px] overflow-y-auto pr-1">
            {displayQueue.map((item) => (
              <div
                key={item.id}
                className="pt-2.5 flex items-center justify-between text-xs gap-3"
              >
                <div className="flex items-center space-x-3 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center flex-shrink-0">
                    {getJobIcon(item.type)}
                  </div>
                  <div className="min-w-0">
                    <span className="font-medium text-zinc-100 block truncate">
                      {item.type === "video" ? "🎬 Next Video: " : "📝 Next Feed Post: "}
                      &ldquo;{item.title}&rdquo;
                    </span>
                    <span className="text-[11px] text-zinc-400 block truncate mt-0.5 flex items-center space-x-1.5">
                      <Clock size={11} className="text-zinc-500" />
                      <span>{item.scheduled_time}</span>
                    </span>
                  </div>
                </div>

                <div className="flex items-center space-x-2 flex-shrink-0">
                  {getStatusBadge(item.status)}
                  {onDeleteJob && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteJob(item.id);
                      }}
                      className="p-1.5 rounded-md text-zinc-500 hover:text-red-400 hover:bg-red-500/10 border border-transparent hover:border-red-500/20 transition-all cursor-pointer group/del"
                      title="Delete scheduled job"
                      aria-label={`Delete job ${item.title}`}
                    >
                      <Trash2 size={13} className="group-hover/del:scale-110 transition-transform" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

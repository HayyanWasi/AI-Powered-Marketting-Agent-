"use client";

import Link from "next/link";
import {
  Send,
  Heart,
  MessageSquare,
  Clock,
  CheckCircle2,
  PauseCircle,
  ChevronRight,
} from "lucide-react";
import { DailyQuotaProgress, ActiveCampaignTracker } from "./types";

interface Props {
  progress: DailyQuotaProgress;
  campaigns: ActiveCampaignTracker[];
  onOpenCampaign?: (campaignId: string, campaignName?: string) => void;
}

export default function LiveTrackingCard({ progress, campaigns, onOpenCampaign }: Props) {
  const connPct = Math.min(
    100,
    Math.round((progress.connections_sent / progress.connections_max) * 100) || 0
  );
  const likesPct = Math.min(
    100,
    Math.round((progress.likes_given / progress.likes_max) * 100) || 0
  );
  const commPct = Math.min(
    100,
    Math.round((progress.comments_posted / progress.comments_max) * 100) || 0
  );

  const getCampaignStatusBadge = (status: ActiveCampaignTracker["status"]) => {
    switch (status) {
      case "ACTIVE":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse mr-1.5" />
            ACTIVE
          </span>
        );
      case "SCHEDULED":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Clock size={11} className="mr-1" />
            SCHEDULED
          </span>
        );
      case "COMPLETED":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-zinc-800 text-zinc-400 border border-zinc-700">
            <CheckCircle2 size={11} className="mr-1" />
            COMPLETED
          </span>
        );
      case "PAUSED":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-zinc-800 text-zinc-400 border border-zinc-700">
            <PauseCircle size={11} className="mr-1" />
            PAUSED
          </span>
        );
    }
  };

  return (
    <div className="rounded-xl bg-zinc-900/60 border border-zinc-800 p-6 shadow-lg backdrop-blur-sm space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-zinc-800">
        <div>
          <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
            Live Campaign Tracking & Progress
          </h2>
          <p className="text-xs text-zinc-400 mt-1">
            Real-time audit of daily engagement velocity and autonomous campaign pipelines.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs text-zinc-400">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>Telemetry Live Stream</span>
        </div>
      </div>

      {/* Part 1: Today's Live Progress (Visual Progress Bars) */}
      <div>
        <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">
          Today&apos;s Live Quota Progress
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Progress 1: Connections (Blue) */}
          <div className="p-4 rounded-lg bg-zinc-950/70 border border-zinc-800/80 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-zinc-300 font-medium flex items-center space-x-2">
                <Send size={14} className="text-blue-400" />
                <span>Connections</span>
              </span>
              <span className="font-mono text-xs text-zinc-100 font-semibold">
                {progress.connections_sent} / {progress.connections_max} sent
              </span>
            </div>

            <div className="w-full h-2 rounded-full bg-zinc-800/80 overflow-hidden">
              <div
                className="h-full rounded-full bg-blue-500 transition-all duration-500"
                style={{ width: `${connPct}%` }}
              />
            </div>

            <div className="flex items-center justify-between text-[11px] text-zinc-500 font-mono">
              <span>Limit fill</span>
              <span>{connPct}%</span>
            </div>
          </div>

          {/* Progress 2: Likes (Violet/Purple) */}
          <div className="p-4 rounded-lg bg-zinc-950/70 border border-zinc-800/80 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-zinc-300 font-medium flex items-center space-x-2">
                <Heart size={14} className="text-purple-400" />
                <span>Likes</span>
              </span>
              <span className="font-mono text-xs text-zinc-100 font-semibold">
                {progress.likes_given} / {progress.likes_max} given
              </span>
            </div>

            <div className="w-full h-2 rounded-full bg-zinc-800/80 overflow-hidden">
              <div
                className="h-full rounded-full bg-purple-500 transition-all duration-500"
                style={{ width: `${likesPct}%` }}
              />
            </div>

            <div className="flex items-center justify-between text-[11px] text-zinc-500 font-mono">
              <span>Limit fill</span>
              <span>{likesPct}%</span>
            </div>
          </div>

          {/* Progress 3: Comments (Emerald) */}
          <div className="p-4 rounded-lg bg-zinc-950/70 border border-zinc-800/80 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-zinc-300 font-medium flex items-center space-x-2">
                <MessageSquare size={14} className="text-emerald-400" />
                <span>Comments</span>
              </span>
              <span className="font-mono text-xs text-zinc-100 font-semibold">
                {progress.comments_posted} / {progress.comments_max} posted
              </span>
            </div>

            <div className="w-full h-2 rounded-full bg-zinc-800/80 overflow-hidden">
              <div
                className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                style={{ width: `${commPct}%` }}
              />
            </div>

            <div className="flex items-center justify-between text-[11px] text-zinc-500 font-mono">
              <span>Limit fill</span>
              <span>{commPct}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Part 2: Active Campaigns Table / List */}
      <div>
        <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">
          Running Campaigns (Autopilot Mode)
        </h3>

        <div className="rounded-lg bg-zinc-950/70 border border-zinc-800/80 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-zinc-800 bg-zinc-900/30 text-[11px] font-medium text-zinc-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Campaign Name</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Last Activity</th>
                  <th className="py-3 px-4">Sprint Progress</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-zinc-800/50 text-xs text-zinc-300">
                {campaigns.map((camp) => (
                  <tr
                    key={camp.campaign_id}
                    onClick={() => onOpenCampaign?.(camp.campaign_id, camp.campaign_name)}
                    className="hover:bg-zinc-800/30 transition-colors group cursor-pointer"
                  >
                    {/* Campaign Name with clickable button or link */}
                    <td className="py-3.5 px-4 font-medium text-zinc-100">
                      {onOpenCampaign ? (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onOpenCampaign(camp.campaign_id, camp.campaign_name);
                          }}
                          className="hover:text-blue-400 hover:underline transition-colors text-left font-medium text-zinc-100 cursor-pointer"
                        >
                          {camp.campaign_name}
                        </button>
                      ) : (
                        <Link
                          href={`/new-campaign?campaign=${camp.campaign_id}`}
                          className="hover:text-blue-400 hover:underline transition-colors inline-block"
                        >
                          {camp.campaign_name}
                        </Link>
                      )}
                    </td>

                    <td className="py-3.5 px-4">
                      {getCampaignStatusBadge(camp.status)}
                    </td>

                    <td className="py-3.5 px-4 text-zinc-400 text-xs font-mono">
                      {camp.last_action}
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="inline-flex items-center space-x-2.5">
                        <div className="w-24 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${camp.status === "ACTIVE"
                                ? "bg-emerald-400"
                                : camp.status === "SCHEDULED"
                                  ? "bg-amber-400"
                                  : "bg-zinc-500"
                              }`}
                            style={{ width: `${camp.progress_pct}%` }}
                          />
                        </div>
                        <span className="font-mono text-xs text-zinc-400 w-8 text-right">
                          {camp.progress_pct}%
                        </span>
                      </div>
                    </td>

                    {/* View Action Column */}
                    <td className="py-3.5 px-4 text-right">
                      {onOpenCampaign ? (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onOpenCampaign(camp.campaign_id, camp.campaign_name);
                          }}
                          className="inline-flex items-center space-x-1 text-xs font-medium text-zinc-400 group-hover:text-blue-400 transition-colors px-2 py-1 rounded hover:bg-zinc-800/60 cursor-pointer"
                          title="Open campaign details"
                        >
                          <span>Open</span>
                          <ChevronRight size={13} className="text-zinc-500 group-hover:text-blue-400 transition-colors" />
                        </button>
                      ) : (
                        <Link
                          href={`/new-campaign?campaign=${camp.campaign_id}`}
                          className="inline-flex items-center space-x-1 text-xs font-medium text-zinc-400 group-hover:text-blue-400 transition-colors px-2 py-1 rounded hover:bg-zinc-800/60 cursor-pointer"
                          title="View campaign launchpad"
                        >
                          <span>View</span>
                          <ChevronRight size={13} className="text-zinc-500 group-hover:text-blue-400 transition-colors" />
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

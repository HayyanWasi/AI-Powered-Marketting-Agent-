"use client";

import { useState, useEffect } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import EngagementSettingsCard from "@/components/prospects/EngagementSettingsCard";
import PublishingScheduleCard from "@/components/prospects/PublishingScheduleCard";
import LiveTrackingCard from "@/components/prospects/LiveTrackingCard";
import PersonasCard from "@/components/prospects/PersonasCard";
import ReviewQueueCard from "@/components/prospects/ReviewQueueCard";
import CircuitBreakerCard from "@/components/prospects/CircuitBreakerCard";
import CampaignDetailsModal from "@/components/campaign/CampaignDetailsModal";
import {
  AutopilotSettings,
  QueueItem,
  DailyQuotaProgress,
  ActiveCampaignTracker,
} from "@/components/prospects/types";
import { autopilotApi } from "@/lib/api";
import { Pause, Play } from "lucide-react";

const initialSettings: AutopilotSettings = {
  daily_connections: 15,
  daily_likes: 20,
  daily_comments: 10,
  post_time_slot: "10:00 AM",
  video_time_slot: "04:00 PM",
};

const initialQueue: QueueItem[] = [
  {
    id: "q-1",
    type: "video",
    title: "AI Product Spotlight Commercial",
    scheduled_time: "Today at 4:00 PM",
    status: "ready",
  },
  {
    id: "q-2",
    type: "post",
    title: "Scaling SaaS Marketing with Autonomous Agents",
    scheduled_time: "Tomorrow at 10:00 AM",
    status: "pending",
  },
];

const initialProgress: DailyQuotaProgress = {
  connections_sent: 5,
  connections_max: 15,
  likes_given: 8,
  likes_max: 20,
  comments_posted: 3,
  comments_max: 10,
};

const initialCampaigns: ActiveCampaignTracker[] = [
  {
    campaign_id: "camp-01",
    campaign_name: "Tier-1 FMCG Replenishment Sprint",
    status: "ACTIVE",
    last_action: "Connection invite sent 12m ago",
    progress_pct: 68,
  },
  {
    campaign_id: "camp-02",
    campaign_name: "LATAM Retail Tienditas Expansion",
    status: "ACTIVE",
    last_action: "Smart comment posted 28m ago",
    progress_pct: 42,
  },
  {
    campaign_id: "camp-03",
    campaign_name: "EU Beverage Route-to-Market Q4",
    status: "SCHEDULED",
    last_action: "Queue dispatch planned at 10:00 AM",
    progress_pct: 15,
  },
  {
    campaign_id: "camp-04",
    campaign_name: "Commercial Credit Pre-Approval Outreach",
    status: "COMPLETED",
    last_action: "Completed yesterday at 5:00 PM",
    progress_pct: 100,
  },
];

export default function ProspectsPage() {
  const [settings, setSettings] = useState<AutopilotSettings>(initialSettings);
  const [queue, setQueue] = useState<QueueItem[]>(initialQueue);
  const [progress, setProgress] = useState<DailyQuotaProgress>(initialProgress);
  const [campaigns, setCampaigns] = useState<ActiveCampaignTracker[]>(initialCampaigns);
  const [isAutopilotActive, setIsAutopilotActive] = useState(true);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const [selectedCampaignName, setSelectedCampaignName] = useState<string | undefined>(undefined);

  useEffect(() => {
    async function loadData() {
      try {
        const [settingsRes, trackerRes] = await Promise.all([
          autopilotApi.getSettings().catch(() => null),
          autopilotApi.getTracker().catch(() => null),
        ]);
        if (settingsRes) {
          setSettings({
            daily_connections: settingsRes.daily_connections,
            daily_likes: settingsRes.daily_likes,
            daily_comments: settingsRes.daily_comments,
            post_time_slot: settingsRes.post_time_slot,
            video_time_slot: settingsRes.video_time_slot,
          });
          if (settingsRes.master_active !== undefined) {
            setIsAutopilotActive(settingsRes.master_active);
          }
        }
        if (trackerRes) {
          if (trackerRes.daily_progress) setProgress(trackerRes.daily_progress);
          if (trackerRes.upcoming_queue) setQueue(trackerRes.upcoming_queue as QueueItem[]);
          if (trackerRes.running_campaigns) setCampaigns(trackerRes.running_campaigns as ActiveCampaignTracker[]);
          if (trackerRes.master_active !== undefined) setIsAutopilotActive(trackerRes.master_active);
        }
      } catch (e) {
        console.warn("Could not load backend autopilot data:", e);
      }
    }
    loadData();
  }, []);

  const handleSaveSettings = async (newSettings: AutopilotSettings) => {
    try {
      await autopilotApi.saveSettings({
        ...newSettings,
        master_active: isAutopilotActive,
      });
    } catch (err) {
      console.warn("Failed to persist settings to backend:", err);
    }
    setSettings(newSettings);

    // Synchronize daily progress maximum limits with the saved settings
    setProgress((prev) => ({
      ...prev,
      connections_max: newSettings.daily_connections,
      likes_max: newSettings.daily_likes,
      comments_max: newSettings.daily_comments,
    }));
  };

  const handleToggleAutopilot = async () => {
    const nextState = !isAutopilotActive;
    setIsAutopilotActive(nextState);
    try {
      await autopilotApi.toggle(nextState);
    } catch (err) {
      console.warn("Failed to toggle autopilot on backend:", err);
    }
  };

  const handleOpenCampaign = (campaignId: string, campaignName?: string) => {
    setSelectedCampaignId(campaignId);
    setSelectedCampaignName(campaignName);
  };

  const handleDeleteJob = async (jobId: string) => {
    // Immediate optimistic removal from UI
    setQueue((prev) => prev.filter((item) => item.id !== jobId));
    try {
      await autopilotApi.deleteQueueItem(jobId);
    } catch (err) {
      console.warn("Failed to delete queued job on backend:", err);
    }
  };

  return (
    <div className="min-h-screen bg-[#0E141B] text-zinc-100 flex flex-col font-sans selection:bg-blue-500/30 selection:text-white">
      {/* Top Navbar */}
      <Navbar />

      {/* Main Container */}
      <main className="flex-1 pt-28 pb-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full space-y-6">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-zinc-800">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-zinc-100 tracking-tight">
              Autopilot Control Room
            </h1>
            <p className="text-xs sm:text-sm text-zinc-400 mt-1.5 max-w-2xl leading-relaxed">
              Configure daily outreach quotas, publishing schedules, and track live automation execution.
            </p>
          </div>

          {/* Master Autopilot Toggle & Live Status Badge */}
          <div className="flex items-center space-x-3 self-start md:self-auto">
            {isAutopilotActive ? (
              <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-xs font-medium text-emerald-400 shadow-sm transition-all">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                </span>
                <span>System Active • Normal Speed</span>
              </div>
            ) : (
              <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-xs font-medium text-amber-400 shadow-sm transition-all">
                <span className="h-2 w-2 rounded-full bg-amber-400" />
                <span>System Paused • Automation Halted</span>
              </div>
            )}

            <button
              type="button"
              onClick={() => setIsAutopilotActive(!isAutopilotActive)}
              className={`h-8 px-3 rounded-lg text-xs font-medium transition-all flex items-center space-x-1.5 border cursor-pointer ${
                isAutopilotActive
                  ? "bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 border-zinc-700 shadow-sm"
                  : "bg-emerald-600 hover:bg-emerald-500 text-zinc-950 font-semibold border-emerald-500 shadow-lg shadow-emerald-950/40"
              }`}
            >
              {isAutopilotActive ? (
                <>
                  <Pause size={12} className="text-amber-400" />
                  <span>Pause Automation</span>
                </>
              ) : (
                <>
                  <Play size={12} className="fill-zinc-950" />
                  <span>Resume Automation</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Circuit Breaker Safety Status */}
        <CircuitBreakerCard />

        {/* 2-Column Responsive Grid: Section 1 & Section 2 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Section 1: Daily Engagement Settings (Quota Control) */}
          <EngagementSettingsCard
            initialSettings={settings}
            onSave={handleSaveSettings}
          />

          {/* Section 2: Publishing Schedule & Upcoming Queue */}
          <PublishingScheduleCard
            settings={settings}
            queue={queue}
            onDeleteJob={handleDeleteJob}
          />
        </div>

        {/* Section 3: Targeting Personas & AI Comment Review Queue */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <PersonasCard />
          <ReviewQueueCard />
        </div>

        {/* Section 4: Live Campaign Tracking & Progress (Full-Width) */}
        <LiveTrackingCard
          progress={progress}
          campaigns={campaigns}
          onOpenCampaign={handleOpenCampaign}
        />
      </main>

      {/* Campaign Details Modal */}
      <CampaignDetailsModal
        campaignId={selectedCampaignId}
        initialCampaignName={selectedCampaignName}
        isOpen={!!selectedCampaignId}
        onClose={() => setSelectedCampaignId(null)}
      />

      {/* Footer */}
      <Footer />
    </div>
  );
}

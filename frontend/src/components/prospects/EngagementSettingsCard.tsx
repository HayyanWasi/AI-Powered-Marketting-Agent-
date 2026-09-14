"use client";

import { useState } from "react";
import {
  UserPlus,
  ThumbsUp,
  MessageSquare,
  ShieldCheck,
  Check,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { AutopilotSettings } from "./types";

interface Props {
  initialSettings: AutopilotSettings;
  onSave: (settings: AutopilotSettings) => Promise<void> | void;
}

const CONSTRAINTS = {
  connections: { min: 1, max: 25 },
  likes: { min: 1, max: 40 },
  comments: { min: 1, max: 15 },
};

export default function EngagementSettingsCard({
  initialSettings,
  onSave,
}: Props) {
  const [settings, setSettings] = useState<AutopilotSettings>(initialSettings);
  const [isSaving, setIsSaving] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  // Individual field validation errors
  const [errors, setErrors] = useState<{
    connections?: string;
    likes?: string;
    comments?: string;
  }>({});

  const validateField = (field: "connections" | "likes" | "comments", value: number) => {
    let errorMsg: string | undefined = undefined;
    if (isNaN(value) || value < CONSTRAINTS[field].min) {
      errorMsg = `Minimum is ${CONSTRAINTS[field].min} per day`;
    } else if (value > CONSTRAINTS[field].max) {
      errorMsg = `Maximum allowed is ${CONSTRAINTS[field].max} per day`;
    }

    setErrors((prev) => ({
      ...prev,
      [field]: errorMsg,
    }));
    return !errorMsg;
  };

  const handleConnectionsChange = (val: number) => {
    setSettings((prev) => ({ ...prev, daily_connections: val }));
    validateField("connections", val);
  };

  const handleLikesChange = (val: number) => {
    setSettings((prev) => ({ ...prev, daily_likes: val }));
    validateField("likes", val);
  };

  const handleCommentsChange = (val: number) => {
    setSettings((prev) => ({ ...prev, daily_comments: val }));
    validateField("comments", val);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const v1 = validateField("connections", settings.daily_connections);
    const v2 = validateField("likes", settings.daily_likes);
    const v3 = validateField("comments", settings.daily_comments);

    if (!v1 || !v2 || !v3) return;

    setIsSaving(true);
    try {
      await onSave(settings);
      setIsSaving(false);
      setIsSaved(true);
      setTimeout(() => setIsSaved(false), 3000);
    } catch {
      setIsSaving(false);
    }
  };

  return (
    <div className="rounded-xl bg-zinc-900/60 border border-zinc-800 p-6 flex flex-col justify-between shadow-lg backdrop-blur-sm">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-zinc-800 mb-6">
          <div>
            <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
              Daily Engagement Settings
            </h2>
            <p className="text-xs text-zinc-400 mt-1">
              Configure daily automation limits and quota controls.
            </p>
          </div>

          <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
            <ShieldCheck size={14} />
            <span>Safe Rate Protected</span>
          </div>
        </div>

        {/* Inputs Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* 1. Daily Connections */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-zinc-300 flex items-center space-x-2">
                <UserPlus size={14} className="text-blue-400" />
                <span>Daily Connection Requests</span>
              </label>
              <span className="text-[11px] font-mono text-zinc-500">
                Range: 1 – 25 / day
              </span>
            </div>

            <div className="relative">
              <input
                type="number"
                value={settings.daily_connections || ""}
                onChange={(e) => handleConnectionsChange(parseInt(e.target.value))}
                className={`w-full h-11 px-3.5 rounded-lg bg-zinc-950/80 border text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 transition-colors font-mono ${
                  errors.connections
                    ? "border-rose-500 focus:ring-rose-500 focus:border-rose-500"
                    : "border-zinc-800 focus:ring-blue-500 focus:border-blue-500"
                }`}
                placeholder="15"
              />
              <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs text-zinc-500 font-sans">
                invites/day
              </span>
            </div>

            {errors.connections && (
              <p className="text-xs text-rose-400 mt-1 flex items-center space-x-1">
                <AlertCircle size={12} />
                <span>{errors.connections}</span>
              </p>
            )}
          </div>

          {/* 2. Daily Post Likes */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-zinc-300 flex items-center space-x-2">
                <ThumbsUp size={14} className="text-purple-400" />
                <span>Daily Post Likes</span>
              </label>
              <span className="text-[11px] font-mono text-zinc-500">
                Range: 1 – 40 / day
              </span>
            </div>

            <div className="relative">
              <input
                type="number"
                value={settings.daily_likes || ""}
                onChange={(e) => handleLikesChange(parseInt(e.target.value))}
                className={`w-full h-11 px-3.5 rounded-lg bg-zinc-950/80 border text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 transition-colors font-mono ${
                  errors.likes
                    ? "border-rose-500 focus:ring-rose-500 focus:border-rose-500"
                    : "border-zinc-800 focus:ring-purple-500 focus:border-purple-500"
                }`}
                placeholder="20"
              />
              <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs text-zinc-500 font-sans">
                likes/day
              </span>
            </div>

            {errors.likes && (
              <p className="text-xs text-rose-400 mt-1 flex items-center space-x-1">
                <AlertCircle size={12} />
                <span>{errors.likes}</span>
              </p>
            )}
          </div>

          {/* 3. Daily Smart Comments */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-zinc-300 flex items-center space-x-2">
                <MessageSquare size={14} className="text-emerald-400" />
                <span>Daily Smart Comments</span>
              </label>
              <span className="text-[11px] font-mono text-zinc-500">
                Range: 1 – 15 / day
              </span>
            </div>

            <div className="relative">
              <input
                type="number"
                value={settings.daily_comments || ""}
                onChange={(e) => handleCommentsChange(parseInt(e.target.value))}
                className={`w-full h-11 px-3.5 rounded-lg bg-zinc-950/80 border text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 transition-colors font-mono ${
                  errors.comments
                    ? "border-rose-500 focus:ring-rose-500 focus:border-rose-500"
                    : "border-zinc-800 focus:ring-emerald-500 focus:border-emerald-500"
                }`}
                placeholder="10"
              />
              <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs text-zinc-500 font-sans">
                comments/day
              </span>
            </div>

            {errors.comments && (
              <p className="text-xs text-rose-400 mt-1 flex items-center space-x-1">
                <AlertCircle size={12} />
                <span>{errors.comments}</span>
              </p>
            )}
          </div>

          {/* Safety Helper Note */}
          <div className="p-3 rounded-lg bg-zinc-950/50 border border-zinc-800/80 text-zinc-400 text-xs flex items-start space-x-2">
            <ShieldCheck size={16} className="text-emerald-400 flex-shrink-0 mt-0.5" />
            <span className="leading-relaxed">
              Quotas are constrained within safe platform limits to protect your LinkedIn account reputation.
            </span>
          </div>

          {/* Save Settings Button */}
          <div className="pt-2 flex justify-end">
            <button
              type="submit"
              disabled={isSaving}
              className={`h-10 px-5 rounded-lg text-xs font-medium flex items-center space-x-2 transition-all cursor-pointer shadow-sm ${
                isSaved
                  ? "bg-emerald-500 text-zinc-950 font-semibold"
                  : "bg-blue-600 hover:bg-blue-500 text-white"
              }`}
            >
              {isSaving ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  <span>Saving Settings...</span>
                </>
              ) : isSaved ? (
                <>
                  <Check size={14} strokeWidth={2.5} />
                  <span>Settings Saved</span>
                </>
              ) : (
                <span>Save Settings</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import Sidebar from "@/components/shell/Sidebar";
import { useAuth } from "@/context/AuthContext";
import { useBrand } from "@/context/BrandContext";
import { useVideoGeneration } from "@/components/video/useVideoGeneration";
import { campaignApi, autopilotApi, Campaign } from "@/lib/api";
import { Film, Loader2, Download, Share2, RotateCcw, ExternalLink } from "lucide-react";

export default function VideoStudioPage() {
  const { user, isLoading: authLoading } = useAuth();
  const { activeBrandId, isLoading: brandsLoading } = useBrand();

  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [campaignId, setCampaignId] = useState<string | null>(null);
  const [campaignsLoading, setCampaignsLoading] = useState(true);
  const [campaignsError, setCampaignsError] = useState<string | null>(null);

  const [prompt, setPrompt] = useState("");
  const [uploadState, setUploadState] = useState<"idle" | "uploading" | "done" | "error">("idle");
  const [uploadMsg, setUploadMsg] = useState("");

  const {
    status,
    currentStage,
    displayProgress,
    error,
    errorStatus,
    artifact,
    startGeneration,
    retry,
  } = useVideoGeneration(campaignId);

  const loadCampaigns = useCallback(async () => {
    if (authLoading || brandsLoading) return;
    if (!user) {
      setCampaigns([]);
      setCampaignId(null);
      setCampaignsLoading(false);
      setCampaignsError(null);
      return;
    }

    setCampaignsLoading(true);
    setCampaignsError(null);

    try {
      const result = await campaignApi.list({
        page_size: 100,
        company_profile_id: activeBrandId || undefined,
      });

      const loadedCampaigns = result.campaigns || [];
      setCampaigns(loadedCampaigns);

      setCampaignId((prevSelected) => {
        if (prevSelected) {
          const stillExists = loadedCampaigns.some((c) => c.id === prevSelected);
          if (stillExists) return prevSelected;
          return null;
        }

        const requested =
          typeof window !== "undefined"
            ? new URLSearchParams(window.location.search).get("campaign")
            : null;
        const matched = loadedCampaigns.find((c) => c.id === requested);
        if (matched) return matched.id;
        return loadedCampaigns.length > 0 ? loadedCampaigns[0].id : null;
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load campaigns";
      setCampaignsError(msg);
      setCampaigns([]);
    } finally {
      setCampaignsLoading(false);
    }
  }, [authLoading, brandsLoading, user, activeBrandId]);

  useEffect(() => {
    if (!authLoading && !brandsLoading && user) {
      const timer = setTimeout(() => {
        void loadCampaigns();
      }, 0);
      return () => clearTimeout(timer);
    } else if (!authLoading && !user) {
      const timer = setTimeout(() => {
        setCampaigns([]);
        setCampaignId(null);
        setCampaignsLoading(false);
        setCampaignsError(null);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [authLoading, brandsLoading, user, loadCampaigns]);

  const isGenerating = status === "queued" || status === "generating";
  const isCompleted = status === "completed" && !!artifact?.videoUrl;
  const isStaleStrategy =
    errorStatus === 409 ||
    (error ? error.toLowerCase().includes("campaign strategy is outdated") : false);

  const handleGenerate = () => {
    const p = prompt.trim();
    if (!p || isGenerating || !campaignId) return;
    setUploadState("idle");
    setUploadMsg("");
    startGeneration(p);
  };

  const handleUpload = async () => {
    const postId = artifact?.schedulerPostId;
    if (!postId) {
      setUploadState("error");
      setUploadMsg("No draft post is linked to this video yet.");
      return;
    }
    setUploadState("uploading");
    setUploadMsg("");
    try {
      const res = await autopilotApi.publishNow(postId);
      if (res.success) {
        setUploadState("done");
        setUploadMsg(res.message || "Published to LinkedIn.");
      } else {
        setUploadState("error");
        setUploadMsg(res.error || "Upload failed. Please retry.");
      }
    } catch (e) {
      setUploadState("error");
      setUploadMsg(e instanceof Error ? e.message : "Upload failed. Please retry.");
    }
  };

  return (
    <div className="flex h-screen bg-[#f6f7f8] text-[#1f2a30] overflow-hidden">
      <Sidebar active="video" />

      <main className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-16 shrink-0 border-b border-[#e6e9ec] bg-white flex items-center justify-between px-4 sm:px-6">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="text-[16px] font-semibold text-[#1f2a30]">Video Studio</h1>
              <span className="text-[10.5px] font-semibold uppercase tracking-wide text-[#1174b8] bg-[#e9f2fa] rounded px-1.5 py-0.5">
                Prompt engine
              </span>
            </div>
            <p className="text-[12.5px] text-[#8a949c] mt-0.5">
              Generate vertical LinkedIn Reels from a prompt
            </p>
          </div>

          {/* Campaign is required by the backend, so it is selectable here. */}
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-[12.5px] text-[#5a6771]">
              <span className="hidden sm:inline">Campaign</span>
              <select
                value={campaignId ?? ""}
                onChange={(e) => setCampaignId(e.target.value || null)}
                disabled={campaignsLoading || isGenerating || campaigns.length === 0}
                className="max-w-[220px] rounded-[8px] border border-[#dfe4e7] bg-white px-2.5 py-1.5 text-[13px] text-[#1f2a30] focus:outline-none focus:border-[#1174b8] focus:ring-2 focus:ring-[#1174b8]/15 disabled:bg-[#f8f9fa] disabled:text-[#8a949c]"
              >
                {campaignsLoading ? (
                  <option value="">Loading campaigns...</option>
                ) : campaignsError ? (
                  <option value="">Failed to load campaigns</option>
                ) : campaigns.length === 0 ? (
                  <option value="">No campaigns available for this brand</option>
                ) : (
                  <option value="">Select campaign</option>
                )}
                {campaigns.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            {campaignsError && (
              <button
                type="button"
                onClick={() => void loadCampaigns()}
                className="inline-flex items-center gap-1 rounded-[6px] border border-[#dce6ec] bg-[#f8fbfa] px-2 py-1 text-[12px] font-medium text-[#c0392b] hover:bg-[#fae5e3]"
                title="Retry loading campaigns"
              >
                <RotateCcw size={12} /> Retry
              </button>
            )}
          </div>
        </header>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-8">
          <div className="max-w-4xl mx-auto grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 items-start">
            {/* Left: prompt card */}
            <section className="rounded-[14px] border border-[#e6e9ec] bg-white p-5 sm:p-6 shadow-sm">
              <h2 className="text-[16px] font-semibold text-[#1f2a30]">Describe your Reel</h2>
              <p className="text-[13px] text-[#8a949c] mt-1 mb-4 leading-relaxed">
                AI writes the script, generates visuals, voiceover, and captions automatically.
              </p>

              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={5}
                disabled={isGenerating}
                aria-label="Describe your Reel"
                placeholder="Create a 30-second punchy Reel explaining why cloud infrastructure teams are switching to eBPF observability. Start with a bold hook about wasted compute costs."
                className="w-full rounded-[10px] border border-[#dfe4e7] bg-[#fbfcfc] px-3.5 py-3 text-[13.5px] leading-relaxed text-[#26333b] placeholder-[#a6afb5] resize-y focus:outline-none focus:border-[#1174b8] focus:ring-2 focus:ring-[#1174b8]/15"
              />

              {campaignsLoading ? (
                <p className="text-[12.5px] text-[#8a949c] mt-2 flex items-center gap-1.5">
                  <Loader2 size={13} className="animate-spin" /> Loading campaigns...
                </p>
              ) : campaignsError ? (
                <div className="mt-2 flex items-center justify-between gap-2 rounded-[8px] border border-[#f5c6cb] bg-[#fdf7f7] px-3 py-2 text-[12.5px] text-[#c0392b]">
                  <span>Failed to load campaigns</span>
                  <button
                    type="button"
                    onClick={() => void loadCampaigns()}
                    className="inline-flex items-center gap-1 text-[12px] font-semibold text-[#c0392b] underline hover:no-underline"
                  >
                    <RotateCcw size={12} /> Retry
                  </button>
                </div>
              ) : campaigns.length === 0 ? (
                <p className="text-[12.5px] text-[#8a949c] mt-2">
                  No campaigns available for this brand
                </p>
              ) : !campaignId ? (
                <p className="text-[12.5px] text-[#9a6212] mt-2">
                  Select a campaign above to generate a Reel.
                </p>
              ) : null}

              <button
                type="button"
                onClick={handleGenerate}
                disabled={!prompt.trim() || isGenerating || !campaignId}
                className="mt-4 w-full inline-flex items-center justify-center gap-2 rounded-[9px] bg-[#1174b8] hover:bg-[#0e5f99] disabled:bg-[#b7cfe2] disabled:cursor-not-allowed text-white text-[14px] font-semibold px-4 py-3 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1174b8]/40"
              >
                {isGenerating ? (
                  <>
                    <Loader2 size={16} className="animate-spin" /> Generating…
                  </>
                ) : (
                  <>
                    <Film size={16} /> Generate Reel
                  </>
                )}
              </button>
            </section>

            {/* Right: phone preview */}
            <section className="flex flex-col items-center">
              <div className="w-full max-w-[320px]">
                <div className="relative rounded-[26px] bg-[#0c1622] border border-[#1c2836] shadow-xl overflow-hidden aspect-[9/16]">
                  {isCompleted ? (
                    <video
                      key={artifact!.videoUrl}
                      src={artifact!.videoUrl}
                      controls
                      playsInline
                      className="w-full h-full object-cover bg-black"
                    />
                  ) : (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-6">
                      {isGenerating ? (
                        <>
                          <Loader2 size={26} className="animate-spin text-[#4aa3dd]" />
                          <p className="text-[12.5px] text-[#c6d3de] mt-4 leading-snug">
                            {currentStage}
                          </p>
                          <div className="w-40 h-1.5 rounded-full bg-white/10 mt-4 overflow-hidden">
                            <div
                              className="h-full bg-[#1e8fe0] rounded-full transition-[width] duration-300"
                              style={{ width: `${Math.round(displayProgress)}%` }}
                            />
                          </div>
                          <p className="text-[11px] text-[#7f93a4] mt-2">
                            {Math.round(displayProgress)}%
                          </p>
                        </>
                      ) : status === "error" ? (
                        <>
                          <p className="text-[13px] text-[#ff9a8f] leading-snug">
                            {error || "Generation failed."}
                          </p>
                          {isStaleStrategy && campaignId ? (
                            <Link
                              href={`/campaigns/${campaignId}?tab=strategy`}
                              className="mt-4 inline-flex items-center gap-1.5 rounded-[8px] bg-[#1174b8] hover:bg-[#0e5f99] text-white text-[12.5px] font-medium px-3.5 py-2 transition-colors cursor-pointer"
                            >
                              <ExternalLink size={13} /> View & Update Campaign Strategy
                            </Link>
                          ) : (
                            <button
                              type="button"
                              onClick={retry}
                              className="mt-4 inline-flex items-center gap-1.5 rounded-[8px] border border-white/20 text-white text-[12.5px] font-medium px-3 py-1.5 hover:bg-white/10"
                            >
                              <RotateCcw size={13} /> Retry
                            </button>
                          )}
                        </>
                      ) : (
                        <>
                          <div className="w-12 h-12 rounded-full bg-white/[0.06] grid place-items-center text-[#5f7386]">
                            <Film size={20} />
                          </div>
                          <p className="text-[12.5px] text-[#8b9db0] mt-3 leading-snug">
                            Your Reel preview will appear here
                          </p>
                        </>
                      )}
                    </div>
                  )}
                </div>

                {/* Actions (only once a real video exists) */}
                {isCompleted && (
                  <div className="mt-4 space-y-2">
                    <button
                      type="button"
                      onClick={handleUpload}
                      disabled={uploadState === "uploading" || uploadState === "done"}
                      className="w-full inline-flex items-center justify-center gap-2 rounded-[9px] bg-[#1174b8] hover:bg-[#0e5f99] disabled:opacity-70 text-white text-[13.5px] font-semibold px-4 py-2.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1174b8]/40"
                    >
                      {uploadState === "uploading" ? (
                        <>
                          <Loader2 size={15} className="animate-spin" /> Uploading…
                        </>
                      ) : uploadState === "done" ? (
                        <>Uploaded to LinkedIn</>
                      ) : (
                        <>
                          <Share2 size={15} /> Upload to LinkedIn
                        </>
                      )}
                    </button>

                    <a
                      href={artifact!.videoUrl}
                      download
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-full inline-flex items-center justify-center gap-2 rounded-[9px] border border-[#dfe4e7] bg-white text-[#5a6771] hover:text-[#1f2a30] hover:bg-[#f4f6f7] text-[13.5px] font-medium px-4 py-2.5 transition-colors"
                    >
                      <Download size={15} /> Download MP4
                    </a>

                    {uploadMsg && (
                      <p
                        className={`text-[12px] text-center ${
                          uploadState === "error" ? "text-[#b3392b]" : "text-[#3a8f6b]"
                        }`}
                      >
                        {uploadMsg}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}

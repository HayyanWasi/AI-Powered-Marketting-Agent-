"use client";

import { useState } from "react";
import {
  X,
  Video,
  RefreshCw,
  Edit3,
  Download,
  Check,
} from "lucide-react";
import { VideoArtifact, VideoGenerationStatus } from "./types";
import VideoPlayerProgress from "./VideoPlayerProgress";

interface Props {
  artifact: VideoArtifact | null;
  status: VideoGenerationStatus;
  displayProgress: number;
  currentStage: string;
  error?: string | null;
  isOpen: boolean;
  onClose: () => void;
  onSelectVariation: (idx: number) => void;
  onUpdatePrompt: (newPrompt: string) => void;
  onRegenerate: () => void;
  onRetry?: () => void;
}

export default function VideoStudioPanel({
  artifact,
  status,
  displayProgress,
  currentStage,
  error,
  isOpen,
  onClose,
  onSelectVariation,
  onUpdatePrompt,
  onRegenerate,
  onRetry,
}: Props) {
  const [isEditingPrompt, setIsEditingPrompt] = useState(false);
  const [editedPrompt, setEditedPrompt] = useState("");

  if (!isOpen || !artifact) return null;

  const activeIdx = artifact.activeVariationIndex ?? 0;
  const activeVariation = artifact.variations[activeIdx] || artifact.variations[0];

  const handleToggleEdit = () => {
    if (!isEditingPrompt) {
      setEditedPrompt(artifact.prompt);
      setIsEditingPrompt(true);
    } else {
      if (editedPrompt.trim()) {
        onUpdatePrompt(editedPrompt.trim());
      }
      setIsEditingPrompt(false);
    }
  };

  const handleDownloadActive = () => {
    if (!activeVariation?.videoUrl) return;
    const a = document.createElement("a");
    a.href = activeVariation.videoUrl;
    a.download = `hipoclipse-video-${activeIdx + 1}.mp4`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0E141B] border-l border-white/[0.08] shadow-xl relative z-20 transition-all duration-200">
      {/* Top Header Bar Matching LinkedIn Drafts Studio */}
      <div className="px-5 py-3.5 border-b border-white/[0.08] bg-[#151D26] flex items-center justify-between flex-shrink-0">
        <div className="flex items-center space-x-2.5">
          <div className="w-7 h-7 rounded-md bg-white/[0.05] border border-white/[0.08] text-[#20B8E5] flex items-center justify-center">
            <Video size={15} />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-xs sm:text-sm font-semibold text-[#F5F7FA] tracking-tight">
                Video Generation Studio
              </h2>
              <span className="text-[11px] text-[#6B7785]">
                • {artifact.variations.length} variations
              </span>
            </div>
          </div>
        </div>

        {/* Top Action Buttons: Regenerate, Edit Prompt, Download */}
        <div className="flex items-center space-x-1.5">
          <button
            type="button"
            onClick={onRegenerate}
            disabled={status === "queued" || status === "generating"}
            title="Regenerate"
            className="p-1.5 rounded-md text-[#9AA6B2] hover:text-[#F5F7FA] hover:bg-white/[0.04] disabled:opacity-40 transition-colors cursor-pointer"
          >
            <RefreshCw
              size={13}
              className={status === "generating" ? "animate-spin text-[#20B8E5]" : ""}
            />
          </button>

          <button
            type="button"
            onClick={handleToggleEdit}
            title="Edit Prompt"
            className="px-2 py-1 rounded-md text-xs font-medium text-[#9AA6B2] hover:text-[#F5F7FA] hover:bg-white/[0.04] transition-colors flex items-center space-x-1 cursor-pointer"
          >
            {isEditingPrompt ? (
              <>
                <Check size={12} className="text-[#10B981]" />
                <span className="text-[#10B981]">Save</span>
              </>
            ) : (
              <>
                <Edit3 size={12} />
                <span className="hidden sm:inline">Edit Prompt</span>
              </>
            )}
          </button>

          {status === "completed" && activeVariation?.videoUrl && (
            <button
              type="button"
              onClick={handleDownloadActive}
              title="Download"
              className="px-2.5 py-1 rounded-md bg-[#20B8E5] hover:bg-[#1BA1CA] text-[#0E141B] font-semibold text-xs transition-colors flex items-center space-x-1 cursor-pointer"
            >
              <Download size={12} />
              <span className="hidden sm:inline">Download</span>
            </button>
          )}

          <button
            type="button"
            onClick={onClose}
            aria-label="Close Studio Panel"
            className="p-1.5 rounded-md text-[#6B7785] hover:text-[#F5F7FA] hover:bg-white/[0.04] transition-colors cursor-pointer ml-1"
          >
            <X size={15} />
          </button>
        </div>
      </div>


      {/* Main Studio Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
        {/* Inline Prompt Editor (if active) */}
        {isEditingPrompt && (
          <div className="p-3.5 rounded-lg bg-[#151D26] border border-white/[0.08] space-y-2">
            <span className="text-[11px] font-semibold text-[#9AA6B2] uppercase tracking-wider block">
              Edit Video Scene Prompt
            </span>
            <textarea
              rows={2}
              value={editedPrompt}
              onChange={(e) => setEditedPrompt(e.target.value)}
              className="w-full bg-[#0E141B] border border-white/[0.1] focus:border-[#20B8E5] rounded-md p-2 text-xs text-[#F5F7FA] focus:outline-none resize-none leading-relaxed"
            />
          </div>
        )}

        {/* 16:9 Landscape Video Player & Progress Bar */}
        <VideoPlayerProgress
          variation={activeVariation}
          status={status}
          displayProgress={displayProgress}
          currentStage={currentStage}
          error={error}
          promptText={artifact.prompt}
          generationDuration={artifact.generationDuration}
          onRetry={onRetry}
        />

        {status === "completed" && (
          <div className="pt-2">
            <button
              type="button"
              onClick={() => alert("🚀 Video queued to LinkedIn Autopilot! View dispatch in /prospects control room.")}
              className="w-full py-2.5 px-4 rounded-lg bg-gradient-to-r from-[#0a66c2] to-[#0077b5] hover:from-[#0077b5] hover:to-[#0a66c2] text-white text-xs font-semibold flex items-center justify-center space-x-2 shadow-lg hover:shadow-cyan-500/20 transition-all cursor-pointer"
            >
              <span>🚀 AUTOPILOT TO LINKEDIN</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

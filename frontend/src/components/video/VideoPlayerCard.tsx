"use client";

import { useState, useRef, useEffect } from "react";
import {
  Play,
  Pause,
  Volume2,
  VolumeX,
  Download,
  Copy,
  Check,
  RotateCcw,
  AlertCircle,
  Film,
  Maximize2,
  Loader2,
} from "lucide-react";
import { VideoArtifact, VideoGenerationStatus } from "./types";

interface Props {
  artifact: VideoArtifact | null;
  status: VideoGenerationStatus;
  displayProgress: number;
  currentStage: string;
  error?: string | null;
  onRetry?: () => void;
}

export default function VideoPlayerCard({
  artifact,
  status,
  displayProgress,
  currentStage,
  error,
  onRetry,
}: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [isPlaying, setIsPlaying] = useState(true);
  const [isMuted, setIsMuted] = useState(true);
  const [copied, setCopied] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  // Auto-play when completed
  useEffect(() => {
    if (status === "completed" && videoRef.current) {
      videoRef.current.currentTime = 0;
      videoRef.current
        .play()
        .then(() => setIsPlaying(true))
        .catch(() => setIsPlaying(false));
    }
  }, [status]);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    videoRef.current.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const handleCopyPrompt = async () => {
    if (!artifact?.prompt) return;
    try {
      await navigator.clipboard.writeText(artifact.prompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    if (!artifact?.videoUrl) return;
    const a = document.createElement("a");
    a.href = artifact.videoUrl;
    a.download = `hipoclipse-video-${Date.now()}.mp4`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
      setDuration(videoRef.current.duration || 0);
    }
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!videoRef.current || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const newTime = (clickX / rect.width) * duration;
    videoRef.current.currentTime = newTime;
    setCurrentTime(newTime);
  };

  return (
    <div className="w-full space-y-3">
      {/* Strict 16:9 Landscape Player Container with Zero Layout Shift */}
      <div
        ref={containerRef}
        className="group relative w-full aspect-video rounded-lg overflow-hidden bg-[#0E141B] border border-white/[0.08] shadow-sm select-none"
      >
        {/* 1. IDLE STATE PLACEHOLDER */}
        {status === "idle" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center bg-[#151D26]">
            <div className="w-11 h-11 rounded-lg bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-[#9AA6B2] mb-3">
              <Film size={20} />
            </div>
            <h3 className="text-sm font-semibold text-[#F5F7FA] mb-1">
              AI Landscape Video Generator
            </h3>
            <p className="text-xs text-[#9AA6B2] max-w-sm leading-relaxed">
              Enter a prompt in the chat to render a 16:9 commercial with temporal camera motion and neural lighting.
            </p>
          </div>
        )}

        {/* 2. LOADING & PROGRESS OVERLAY (QUEUED OR GENERATING) */}
        {(status === "queued" || status === "generating") && (
          <div className="absolute inset-0 z-30 flex flex-col items-center justify-center p-6 sm:p-8 bg-[#0E141B]/95 backdrop-blur-md">
            <div className="w-full max-w-sm space-y-4 text-center">
              {/* Stage Info */}
              <div className="space-y-1.5">
                <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-white/[0.05] border border-white/[0.08] text-[11px] font-medium text-[#F5F7FA]">
                  <Loader2 size={12} className="animate-spin text-[#20B8E5]" />
                  <span>16:9 Landscape Render</span>
                </div>

                <h4 className="text-xs sm:text-sm font-medium text-[#F5F7FA] tracking-tight">
                  {currentStage}
                </h4>
              </div>

              {/* High-Contrast Progress Bar with Client-Side Smooth Gliding */}
              <div className="space-y-1.5">
                <div className="w-full h-2 rounded-full bg-white/[0.08] overflow-hidden p-0.5">
                  <div
                    className="h-full rounded-full bg-[#20B8E5] transition-[width] duration-150 ease-linear shadow-sm"
                    style={{ width: `${Math.max(displayProgress, 2)}%` }}
                  />
                </div>

                <div className="flex items-center justify-between text-[11px] text-[#6B7785] font-mono">
                  <span>{status === "queued" ? "Queued" : "Inference"}</span>
                  <span className="text-[#F5F7FA] font-medium">
                    {Math.round(displayProgress)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 3. ERROR STATE OVERLAY */}
        {status === "error" && (
          <div className="absolute inset-0 z-30 flex flex-col items-center justify-center p-6 text-center bg-[#0E141B]/95 backdrop-blur-md">
            <div className="w-10 h-10 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mb-2.5">
              <AlertCircle size={20} />
            </div>

            <h4 className="text-sm font-semibold text-[#F5F7FA] mb-1">
              Generation Error
            </h4>
            <p className="text-xs text-[#9AA6B2] max-w-sm mb-4 leading-relaxed">
              {error || "GPU compute cluster timeout occurred during temporal synthesis."}
            </p>

            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="px-3.5 py-1.5 rounded-md bg-[#F5F7FA] text-[#0E141B] hover:bg-white font-medium text-xs flex items-center space-x-1.5 transition-colors cursor-pointer"
              >
                <RotateCcw size={13} />
                <span>Retry Generation</span>
              </button>
            )}
          </div>
        )}

        {/* 4. COMPLETED VIDEO PLAYER */}
        {status === "completed" && artifact?.videoUrl && (
          <>
            {/* Native Video Element */}
            <video
              ref={videoRef}
              src={artifact.videoUrl}
              poster={artifact.posterUrl}
              loop
              muted={isMuted}
              playsInline
              autoPlay
              onTimeUpdate={handleTimeUpdate}
              onClick={togglePlay}
              className="w-full h-full object-cover cursor-pointer"
            />

            {/* Top Info Badges (Fade in on Hover) */}
            <div className="absolute top-3 left-3 right-3 flex items-center justify-between z-20 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
              <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-[#0E141B]/80 backdrop-blur-md border border-white/[0.08] text-[11px] font-medium text-[#F5F7FA]">
                <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />
                <span>16:9 HD</span>
              </div>

              {/* Copy Prompt Button */}
              <button
                type="button"
                onClick={handleCopyPrompt}
                aria-label="Copy prompt"
                className="pointer-events-auto px-2.5 py-1 rounded-md bg-[#0E141B]/80 hover:bg-[#0E141B] backdrop-blur-md border border-white/[0.08] text-[11px] font-medium text-[#9AA6B2] hover:text-[#F5F7FA] flex items-center space-x-1.5 transition-colors cursor-pointer"
              >
                {copied ? (
                  <>
                    <Check size={12} className="text-[#10B981]" />
                    <span className="text-[#10B981]">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy size={12} />
                    <span>Copy Prompt</span>
                  </>
                )}
              </button>
            </div>

            {/* Bottom Minimalist Controls Overlay (Fade in on Hover) */}
            <div className="absolute inset-x-0 bottom-0 z-20 pt-8 pb-3 px-3.5 bg-gradient-to-t from-black/90 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex flex-col justify-end">
              {/* Progress Scrubber Bar */}
              <div
                onClick={handleSeek}
                className="w-full h-1 bg-white/20 hover:h-2 rounded-full mb-2.5 cursor-pointer relative transition-all"
              >
                <div
                  className="h-full bg-[#20B8E5] rounded-full relative"
                  style={{
                    width: `${duration ? (currentTime / duration) * 100 : 0}%`,
                  }}
                />
              </div>

              {/* Controls Bar */}
              <div className="flex items-center justify-between text-[#F5F7FA]">
                <div className="flex items-center space-x-2">
                  {/* Play / Pause Toggle */}
                  <button
                    type="button"
                    onClick={togglePlay}
                    aria-label={isPlaying ? "Pause" : "Play"}
                    className="w-7 h-7 rounded-md bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors cursor-pointer"
                  >
                    {isPlaying ? <Pause size={14} /> : <Play size={14} />}
                  </button>

                  {/* Volume / Mute Toggle */}
                  <button
                    type="button"
                    onClick={toggleMute}
                    aria-label={isMuted ? "Unmute" : "Mute"}
                    className="w-7 h-7 rounded-md bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors cursor-pointer"
                  >
                    {isMuted ? <VolumeX size={14} /> : <Volume2 size={14} />}
                  </button>

                  {/* Duration Display */}
                  <span className="text-[11px] font-mono text-[#9AA6B2] pl-1">
                    {Math.floor(currentTime)}s / {Math.floor(duration || 15)}s
                  </span>
                </div>

                <div className="flex items-center space-x-1.5">
                  {/* Download MP4 Button */}
                  <button
                    type="button"
                    onClick={handleDownload}
                    aria-label="Download video"
                    className="px-2.5 py-1 rounded-md bg-white/10 hover:bg-white/20 text-xs font-medium flex items-center space-x-1.5 transition-colors cursor-pointer"
                  >
                    <Download size={13} />
                    <span className="hidden sm:inline">Download</span>
                  </button>

                  {/* Fullscreen Button */}
                  <button
                    type="button"
                    onClick={handleFullscreen}
                    aria-label="Toggle Fullscreen"
                    className="w-7 h-7 rounded-md bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors cursor-pointer"
                  >
                    <Maximize2 size={13} />
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Under-Player Metadata Details (When video is completed) */}
      {status === "completed" && artifact && (
        <div className="p-3.5 rounded-lg bg-[#151D26] border border-white/[0.08] flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 text-xs">
          <div>
            <span className="font-medium text-[#F5F7FA] block mb-0.5">
              Scene Specification
            </span>
            <p className="text-[#9AA6B2] text-[11px] leading-relaxed max-w-md">
              &ldquo;{artifact.prompt}&rdquo;
            </p>
          </div>

          <div className="flex items-center space-x-2 text-[11px] text-[#6B7785] font-mono flex-shrink-0">
            <span className="px-2 py-0.5 rounded bg-white/[0.04] border border-white/[0.06]">1920x1080 Landscape</span>
            <span className="px-2 py-0.5 rounded bg-white/[0.04] border border-white/[0.06]">60 FPS</span>
          </div>
        </div>
      )}
    </div>
  );
}

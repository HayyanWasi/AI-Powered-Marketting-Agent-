"use client";

import { useState, useRef, useEffect } from "react";
import {
  Play,
  Pause,
  Volume2,
  VolumeX,
  Download,
  RotateCcw,
  AlertCircle,
  Film,
  Maximize2,
} from "lucide-react";
import { ClimbingBoxLoader } from "react-spinners";
import { VideoVariation, VideoGenerationStatus } from "./types";

interface Props {
  variation: VideoVariation | null;
  status: VideoGenerationStatus;
  displayProgress: number;
  currentStage: string;
  error?: string | null;
  promptText: string;
  generationDuration?: number;
  onRetry?: () => void;
}

export default function VideoPlayerProgress({
  variation,
  status,
  displayProgress,
  currentStage,
  error,
  promptText,
  generationDuration = 15.0,
  onRetry,
}: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [isPlaying, setIsPlaying] = useState(true);
  const [isMuted, setIsMuted] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [videoLoadError, setVideoLoadError] = useState(false);

  // Auto-play when completed
  useEffect(() => {
    setVideoLoadError(false);
    if (status === "completed" && videoRef.current) {
      videoRef.current.currentTime = 0;
      videoRef.current
        .play()
        .then(() => setIsPlaying(true))
        .catch(() => setIsPlaying(false));
    }
  }, [status, variation?.videoUrl]);

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

  const toggleMute = (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!videoRef.current) return;
    videoRef.current.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const handleDownload = (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!variation?.videoUrl) return;
    const a = document.createElement("a");
    a.href = variation.videoUrl;
    a.download = `hipoclipse-reel-${Date.now()}.mp4`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleFullscreen = (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
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
    e.stopPropagation();
    if (!videoRef.current || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const newTime = (clickX / rect.width) * duration;
    videoRef.current.currentTime = newTime;
    setCurrentTime(newTime);
  };

  return (
    <div className="w-full space-y-3">
      {/* Main Video Container: Clean vertical Reel mode */}
      <div
        ref={containerRef}
        className="group relative overflow-hidden bg-black select-none transition-all duration-300 w-full max-w-[340px] sm:max-w-[360px] aspect-[9/16] mx-auto rounded-2xl border border-white/[0.12] shadow-2xl"
      >
        {/* 1. IDLE STATE PLACEHOLDER */}
        {status === "idle" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center bg-[#151D26]">
            <div className="w-12 h-12 rounded-xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-[#20B8E5] mb-3">
              <Film size={22} />
            </div>
            <h3 className="text-sm font-semibold text-[#F5F7FA] mb-1">
              Vertical Reel Studio
            </h3>
            <p className="text-xs text-[#9AA6B2] max-w-xs leading-relaxed">
              Describe your scene on the left to render your promotional video.
            </p>
          </div>
        )}

        {/* 2. PROGRESS OVERLAY (QUEUED / GENERATING) */}
        {(status === "queued" || status === "generating") && (
          <div className="absolute inset-0 z-30 flex flex-col items-center justify-center p-6 sm:p-8 bg-[#0E141B]/95 backdrop-blur-md">
            <div className="w-full max-w-xs space-y-4 text-center">
              {/* ClimbingBoxLoader */}
              <div className="py-2 flex items-center justify-center">
                <ClimbingBoxLoader color="#00c2ee" size={15} />
              </div>

              {/* Stage indicator */}
              <div className="space-y-1.5">
                <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full bg-[#151D26] border border-white/[0.08] text-xs font-medium text-[#F5F7FA]">
                  <span className="w-2 h-2 rounded-full bg-[#00c2ee] animate-pulse" />
                  <span>{currentStage}</span>
                </div>
                <p className="text-[11px] text-[#00c2ee] animate-pulse font-medium">
                  Generating video... This may take some time
                </p>
              </div>

              {/* High-Contrast Progress Bar */}
              <div className="space-y-1.5">
                <div className="w-full h-2 rounded-full bg-white/[0.08] overflow-hidden p-0.5">
                  <div
                    className="h-full rounded-full bg-[#00c2ee] transition-[width] duration-150 ease-linear shadow-sm"
                    style={{ width: `${Math.max(displayProgress, 3)}%` }}
                  />
                </div>

                <div className="flex items-center justify-end text-[11px] text-[#6B7785] font-mono">
                  <span className="text-[#F5F7FA] font-medium">
                    {Math.round(displayProgress)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 3. ERROR OVERLAY */}
        {status === "error" && (
          <div className="absolute inset-0 z-30 flex flex-col items-center justify-center p-6 text-center bg-[#0E141B]/95 backdrop-blur-md">
            <div className="w-10 h-10 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mb-2.5">
              <AlertCircle size={20} />
            </div>

            <h4 className="text-sm font-semibold text-[#F5F7FA] mb-1">
              Generation Error
            </h4>
            <p className="text-xs text-[#9AA6B2] max-w-xs mb-4 leading-relaxed">
              {error || "Video generation encountered an error."}
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

        {/* 4. COMPLETED VIDEO PLAYER: Clean video with no text/buttons obscuring the content */}
        {status === "completed" && variation?.videoUrl && (
          <>
            <video
              ref={videoRef}
              src={variation.videoUrl}
              poster={variation.posterUrl}
              loop
              muted={isMuted}
              playsInline
              autoPlay
              onTimeUpdate={handleTimeUpdate}
              onError={() => setVideoLoadError(true)}
              onClick={togglePlay}
              className={`w-full h-full object-cover cursor-pointer ${videoLoadError ? "hidden" : "block"}`}
            />

            {/* Video Load Error Fallback Overlay */}
            {videoLoadError && (
              <div className="absolute inset-0 z-20 flex flex-col items-center justify-center p-6 text-center bg-[#0E141B]">
                <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center mb-2.5">
                  <AlertCircle size={20} />
                </div>
                <h4 className="text-sm font-semibold text-[#F5F7FA] mb-1">
                  Video Stream Unreachable
                </h4>
                <p className="text-xs text-[#9AA6B2] max-w-xs mb-4 leading-relaxed">
                  The video was generated, but the browser could not load the video stream directly.
                </p>
                <a
                  href={variation.videoUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3.5 py-1.5 rounded-md bg-[#20B8E5] text-[#0E141B] font-medium text-xs flex items-center space-x-1.5 transition-colors cursor-pointer hover:bg-[#1ca3cc]"
                >
                  <Download size={13} />
                  <span>Open / Download Video</span>
                </a>
              </div>
            )}

            {/* Tap to Play / Pause Central Indicator (Only shown when paused) */}
            {!isPlaying && (
              <div
                onClick={togglePlay}
                className="absolute inset-0 z-20 flex items-center justify-center bg-black/30 cursor-pointer"
              >
                <div className="w-14 h-14 rounded-full bg-black/60 backdrop-blur-md border border-white/20 flex items-center justify-center text-white pl-1 shadow-lg">
                  <Play size={24} />
                </div>
              </div>
            )}

            {/* Clean Controls Overlay (Fades in on hover) */}
            <div className="absolute inset-x-0 bottom-0 z-20 pt-8 pb-3 px-3.5 bg-gradient-to-t from-black/90 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex flex-col justify-end">
              {/* Progress Scrubber */}
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
                  <button
                    type="button"
                    onClick={togglePlay}
                    aria-label={isPlaying ? "Pause" : "Play"}
                    className="w-7 h-7 rounded-md bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors cursor-pointer"
                  >
                    {isPlaying ? <Pause size={14} /> : <Play size={14} />}
                  </button>

                  <button
                    type="button"
                    onClick={toggleMute}
                    aria-label={isMuted ? "Unmute" : "Mute"}
                    className="w-7 h-7 rounded-md bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors cursor-pointer"
                  >
                    {isMuted ? <VolumeX size={14} /> : <Volume2 size={14} />}
                  </button>

                  <span className="text-[11px] font-mono text-[#9AA6B2] pl-1">
                    {Math.floor(currentTime)}s / {Math.floor(duration || 15)}s
                  </span>
                </div>

                <div className="flex items-center space-x-1.5">
                  <button
                    type="button"
                    onClick={handleDownload}
                    aria-label="Download video"
                    className="px-2.5 py-1 rounded-md bg-white/10 hover:bg-white/20 text-xs font-medium flex items-center space-x-1.5 transition-colors cursor-pointer"
                  >
                    <Download size={13} />
                    <span className="hidden sm:inline">Download</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleFullscreen}
                    aria-label="Fullscreen"
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

      {/* Card Footer: Metadata below the video, not written on top of it */}
      {status === "completed" && (
        <div className="p-3 rounded-lg bg-[#151D26] border border-white/[0.08] flex items-center justify-between gap-2 text-xs">
          <div className="flex-1 min-w-0 pr-4">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#6B7785] block mb-0.5">
              Scene Prompt
            </span>
            <p className="text-[#F5F7FA] text-xs truncate leading-snug">
              &ldquo;{promptText}&rdquo;
            </p>
          </div>

          <div className="flex items-center space-x-2 text-[11px] text-[#9AA6B2] flex-shrink-0">
            <span className="px-2 py-0.5 rounded bg-white/[0.04] border border-white/[0.08] text-[#F5F7FA]">
              1080p Full HD
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

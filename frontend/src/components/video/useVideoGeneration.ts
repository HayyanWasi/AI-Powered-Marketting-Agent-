"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { VideoGenerationStatus, VideoArtifact, VideoVariation } from "./types";
import { videoApi, ApiError } from "@/lib/api";

interface GenerationOptions {
  forceError?: boolean;
}

export function useVideoGeneration(campaignId: string | null) {
  const [status, setStatus] = useState<VideoGenerationStatus>("idle");
  const [currentStage, setCurrentStage] = useState("Waiting to generate...");
  const [targetProgress, setTargetProgress] = useState(0);
  const [displayProgress, setDisplayProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [currentPrompt, setCurrentPrompt] = useState("");
  const [artifact, setArtifact] = useState<VideoArtifact | null>(null);

  const animationFrameRef = useRef<number | null>(null);
  const targetProgressRef = useRef(0);
  const displayProgressRef = useRef(0);
  const abortControllerRef = useRef<boolean>(false);

  useEffect(() => {
    targetProgressRef.current = targetProgress;
  }, [targetProgress]);

  // Smooth linear interpolation (LERP) loop for progress bar gliding
  useEffect(() => {
    if (status !== "queued" && status !== "generating") return;

    let isRunning = true;

    const smoothStep = () => {
      if (!isRunning) return;

      const current = displayProgressRef.current;
      const target = targetProgressRef.current;
      const delta = target - current;

      if (Math.abs(delta) > 0.05) {
        const next = current + delta * 0.08;
        displayProgressRef.current = next;
        setDisplayProgress(Number(next.toFixed(1)));
      } else {
        displayProgressRef.current = target;
        setDisplayProgress(target);
      }

      animationFrameRef.current = requestAnimationFrame(smoothStep);
    };

    animationFrameRef.current = requestAnimationFrame(smoothStep);

    return () => {
      isRunning = false;
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [status]);

  const startGeneration = useCallback(
    async (prompt: string, options?: GenerationOptions) => {
      if (!campaignId) {
        setStatus("error");
        setError("Select a campaign before generating a video.");
        return;
      }
      abortControllerRef.current = false;
      setStatus("generating");
      setError(null);
      setErrorStatus(null);
      setCurrentPrompt(prompt);
      setTargetProgress(15);
      setDisplayProgress(0);
      displayProgressRef.current = 0;
      setCurrentStage("AI Director: Scripting Scene Breakdown (15%)...");

      const artifactId = `vid-${Date.now()}`;
      const defaultVariations: VideoVariation[] = [
        {
          id: `var-1-${Date.now()}`,
          label: "Campaign video (9:16 Reel)",
          durationSeconds: 15,
          resolution: "1080p HD",
          aspectRatio: "9:16",
          fps: 24,
        },
      ];

      setArtifact({
        id: artifactId,
        title: prompt.slice(0, 36) + (prompt.length > 36 ? "..." : ""),
        prompt,
        status: "generating",
        progress: 15,
        displayProgress: 0,
        currentStage: "AI Director: Scripting Scene Breakdown (15%)...",
        variations: defaultVariations,
        activeVariationIndex: 0,
        createdAt: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      });

      let progressInterval: NodeJS.Timeout | null = null;

      try {
        if (options?.forceError) {
          throw new Error("Cluster GPU timeout: Motion synthesizer encountered memory pressure.");
        }

        // Live progressive stage indicators during synthesis
        let secondsElapsed = 0;
        progressInterval = setInterval(() => {
          if (abortControllerRef.current) return;
          secondsElapsed++;

          if (secondsElapsed === 2) {
            setTargetProgress(30);
            setCurrentStage("Pollinations AI: Synthesizing 720p Scene Visuals (30%)...");
          } else if (secondsElapsed === 8) {
            setTargetProgress(55);
            setCurrentStage("Edge-TTS: Synthesizing Neural Voiceover (55%)...");
          } else if (secondsElapsed === 16) {
            setTargetProgress(75);
            setCurrentStage("MoviePy: Compositing 720p HD Video & Subtitles (75%)...");
          } else if (secondsElapsed === 28) {
            setTargetProgress(90);
            setCurrentStage("FFmpeg: High-Speed Hardware MP4 Encoding (90%)...");
          } else if (secondsElapsed === 42) {
            setTargetProgress(96);
            setCurrentStage("Finalizing 720p HD Video & Audio Equalization (96%)...");
          }
        }, 1000);

        // Await the real backend generation without arbitrary client-side timeout
        const res = await videoApi.generate(campaignId, prompt);

        if (progressInterval) clearInterval(progressInterval);

        let finalVideoUrl = res?.video_url;

        // If deployed and backend returned localhost:8000 URL, rewrite to real backend host
        if (finalVideoUrl && finalVideoUrl.startsWith("http://localhost:8000")) {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL;
          if (apiUrl && !apiUrl.includes("localhost")) {
            const baseUrl = apiUrl.replace(/\/api\/?$/, "");
            finalVideoUrl = finalVideoUrl.replace("http://localhost:8000", baseUrl);
          }
        }

        if (!finalVideoUrl) {
          throw new Error("Backend completed without returning a video URL.");
        }

        setTargetProgress(100);
        setDisplayProgress(100);
        displayProgressRef.current = 100;
        setStatus("completed");
        setCurrentStage("Render Completed");

        const completedVariations: VideoVariation[] = [
          {
            ...defaultVariations[0],
            videoUrl: finalVideoUrl,
          },
        ];

        setArtifact((prev) =>
          prev
            ? {
                ...prev,
                status: "completed",
                progress: 100,
                displayProgress: 100,
                currentStage: "Render Completed",
                videoUrl: finalVideoUrl,
                variations: completedVariations,
                generationDuration: secondsElapsed,
                campaignAssetId: res.asset?.id,
                schedulerPostId: res.draft_post?.id || res.draft_post?.post_id,
              }
            : null
        );
      } catch (err: unknown) {
        if (progressInterval) clearInterval(progressInterval);

        const isExpectedBusinessError =
          err instanceof ApiError && (err.status === 409 || err.status === 422);

        const errorMsg =
          err instanceof Error
            ? err.message
            : "Video generation failed. Please verify the backend service status.";

        if (isExpectedBusinessError) {
          console.warn(`[VideoGen Validation] ${err.status}: ${errorMsg}`);
        } else {
          console.error("[VideoGen Error]", err);
        }

        setStatus("error");
        setError(errorMsg);
        setErrorStatus(err instanceof ApiError ? err.status : null);
        setCurrentStage("Generation Failed");
        setArtifact((prev) =>
          prev
            ? {
                ...prev,
                status: "error",
                error: errorMsg,
                currentStage: "Generation Failed",
              }
            : null
        );
      }
    },
    [campaignId]
  );

  const selectVariation = useCallback((index: number) => {
    setArtifact((prev) =>
      prev ? { ...prev, activeVariationIndex: index } : null
    );
  }, []);

  const updatePrompt = useCallback((newPrompt: string) => {
    setArtifact((prev) =>
      prev ? { ...prev, prompt: newPrompt } : null
    );
  }, []);

  const retry = useCallback(() => {
    if (currentPrompt) startGeneration(currentPrompt);
  }, [currentPrompt, startGeneration]);

  const reset = useCallback(() => {
    abortControllerRef.current = true;
    if (animationFrameRef.current)
      cancelAnimationFrame(animationFrameRef.current);
    setStatus("idle");
    setCurrentStage("Waiting to generate...");
    setTargetProgress(0);
    setDisplayProgress(0);
    setError(null);
    setErrorStatus(null);
    setArtifact(null);
  }, []);

  const effectiveDisplayProgress =
    status === "completed" ? 100 : displayProgress;

  return {
    status,
    currentStage,
    targetProgress,
    displayProgress: effectiveDisplayProgress,
    error,
    errorStatus,
    artifact,
    startGeneration,
    selectVariation,
    updatePrompt,
    retry,
    reset,
  };
}

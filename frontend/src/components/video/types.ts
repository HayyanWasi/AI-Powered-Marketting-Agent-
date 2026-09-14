export type VideoGenerationStatus = "idle" | "queued" | "generating" | "completed" | "error";

export interface VideoVariation {
  id: string;
  label: string; // "Variation 1 (16:9)" | "Variation 2 (16:9)"
  videoUrl?: string;
  posterUrl?: string;
  durationSeconds: number;
  resolution: "1080p HD";
  aspectRatio: "9:16" | "16:9";
  fps: number;
}

export interface VideoProgressEvent {
  jobId: string;
  status: VideoGenerationStatus;
  stage: string;
  targetProgress: number; // 0 to 100
  videoUrl?: string;
  posterUrl?: string;
  durationSeconds?: number;
  error?: string;
}

export interface VideoArtifact {
  id: string;
  title: string;
  prompt: string;
  status: VideoGenerationStatus;
  progress: number;
  displayProgress: number; // Smoothly interpolated progress (0-100)
  currentStage: string;
  error?: string;
  videoUrl?: string;
  posterUrl?: string;
  variations: VideoVariation[];
  activeVariationIndex: number;
  createdAt: string;
  generationDuration?: number;
}

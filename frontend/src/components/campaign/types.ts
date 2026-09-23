export interface ThoughtStep {
  id: string;
  title: string;
  detail?: string;
  timestamp: string;
}

export interface LinkedInPost {
  id: string;
  tag: string; // e.g. "Variation 1 • The Contrarian Hook"
  content: string;
  authorName: string;
  authorTitle: string;
  authorAvatar?: string;
  scheduledAt?: string;
  timezone?: string;
  mediaUrl?: string;
  mediaType?: "video";
  // Stable calendar ordinal used to keep posts in intended order even when
  // progressive completion events arrive out of order.
  orderIndex?: number;
  // A provisional preview is a completed post shown before the campaign's
  // atomic persistence succeeds; it is replaced by the canonical saved post.
  provisional?: boolean;
}

export interface StrategyPillar {
  title: string;
  angle: string;
  hook: string;
}

export interface CampaignStrategy {
  campaignType?: string;
  campaignName?: string;
  eventName: string;
  category?: string;
  date?: string;
  dateLabel?: string;
  eventDate?: string;
  venue?: string;
  ticketPrice?: string;
  capacity?: string;
  registrationLink?: string;
  ctaUrl?: string;
  ctaLabel?: string;
  guestSpeaker?: string;
  targetAudience?: string;
  curriculum?: string;
  objective?: string;
  valueProposition?: string;
  executiveSummary: string;
  pillars: StrategyPillar[];
  distributionSchedule: string[];
  kpis: string[];
  researchStatus?: "available" | "no_evidence" | "degraded" | "not_requested";
  researchStatusReason?: string;
}

export interface LinkedInArtifact {
  id: string;
  /** The real backend campaign id this artifact was generated for. */
  campaignId?: string;
  title: string;
  campaignGoal: string;
  strategy?: CampaignStrategy;
  posts: LinkedInPost[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  thoughts?: ThoughtStep[];
  thoughtDuration?: number;
  isThinking?: boolean;
  isStreaming?: boolean;
  artifactId?: string;
}

export type CampaignStreamEvent =
  | { type: "thought"; step: ThoughtStep }
  | { type: "content"; chunk: string }
  | { type: "artifact_start"; id: string; campaignId: string; title: string; campaignGoal: string; strategy?: CampaignStrategy }
  | { type: "artifact_strategy"; strategy: CampaignStrategy }
  | { type: "artifact_post_add"; post: LinkedInPost }
  | { type: "artifact_post_chunk"; postId: string; chunk: string }
  | { type: "artifact_posts_set"; posts: LinkedInPost[] }
  | { type: "done"; totalDuration: number };

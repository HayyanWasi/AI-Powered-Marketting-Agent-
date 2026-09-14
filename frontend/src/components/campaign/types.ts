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
}

export interface StrategyPillar {
  title: string;
  angle: string;
  hook: string;
}

export interface CampaignStrategy {
  eventName: string;
  category: string;
  eventDate: string;
  venue: string;
  ticketPrice: string;
  capacity?: string;
  registrationLink: string;
  guestSpeaker?: string;
  targetAudience: string;
  curriculum: string;
  executiveSummary: string;
  pillars: StrategyPillar[];
  distributionSchedule: string[];
  kpis: string[];
}

export interface LinkedInArtifact {
  id: string;
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
  | { type: "artifact_start"; id: string; title: string; campaignGoal: string; strategy?: CampaignStrategy }
  | { type: "artifact_strategy"; strategy: CampaignStrategy }
  | { type: "artifact_post_add"; post: LinkedInPost }
  | { type: "artifact_post_chunk"; postId: string; chunk: string }
  | { type: "done"; totalDuration: number };

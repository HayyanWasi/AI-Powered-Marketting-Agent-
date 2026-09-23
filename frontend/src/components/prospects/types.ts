export interface AutopilotSettings {
  daily_connections: number; // default/cap: 25
  daily_likes: number;       // default/cap: 40
  daily_comments: number;    // default/cap: 15
  post_time_slot: string;    // e.g. "10:00 AM"
  video_time_slot: string;   // e.g. "04:00 PM"
}

export interface QueueItem {
  id: string;
  type: "video" | "post" | "sequence";
  title: string;
  scheduled_time: string; // e.g. "Today at 4:00 PM"
  status: "pending" | "uploading" | "ready";
}

export interface DailyQuotaProgress {
  connections_sent: number;
  connections_max: number;
  likes_given: number;
  likes_max: number;
  comments_posted: number;
  comments_max: number;
}

export interface ActiveCampaignTracker {
  campaign_id: string;
  campaign_name: string;
  status: "ACTIVE" | "SCHEDULED" | "COMPLETED" | "PAUSED";
  last_action: string;
  progress_pct: number;
}

/**
 * Centralized API client for the AI Marketing Agent backend.
 *
 * All requests hit the FastAPI backend at NEXT_PUBLIC_API_URL.
 * The backend returns a consistent JSON envelope:
 *   Success: { status: "success", data: T, message: string, timestamp: string }
 *   Error:   { status: "error", error: string, message: string, details: any, timestamp: string }
 *
 * Note: Auth is in MVP mode - backend accepts all requests without tokens.
 *
 * ENDPOINT COVERAGE: 34/34 endpoints across 9 modules
 *  Company (10): create, list, get, update, delete, getBrandInfo,
 *                uploadImages, removeImage, replaceImage, reorderImages
 *  Campaigns (11): create, list, get, update, delete, transition,
 *                  archive, restore, history, createAsset, listAssets
 *  Validation (2): validate, previewCheck
 *  Guest (1): search
 *  Campaign Images (1): generate
 *  AI Generation (7): generate, regenerateText, regenerateStrategy,
 *                     regenerateImage, validate, health, info
 *  Workflow (4): execute, getStatus, approve, reject
 *  Image Processing (1): validate
 *  Operations (2): getMetrics, getHistory
 *  Health (3): check, ready, live
 */

import { getActiveAccessToken } from '@/context/AuthContext';

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'
    ? 'https://ai-powered-marketting-agent.onrender.com/api'
    : 'http://localhost:8000/api');

// ─── Generic helpers ────────────────────────────────────────────────

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  const token = getActiveAccessToken();
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  // Handle 204 No Content
  if (res.status === 204) {
    return undefined as T;
  }

  const json = await res.json();

  if (!res.ok) {
    throw new ApiError(res.status, json.message || json.detail || 'Request failed', json);
  }

  // Unwrap the standard envelope if present
  if (json && typeof json === 'object' && 'data' in json) {
    return json.data as T;
  }

  return json as T;
}

async function get<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'GET' });
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  });
}

async function put<T>(path: string, body?: unknown, extraHeaders?: Record<string, string>): Promise<T> {
  return request<T>(path, {
    method: 'PUT',
    body: body ? JSON.stringify(body) : undefined,
    headers: extraHeaders,
  });
}

async function patch<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: 'PATCH',
    body: body ? JSON.stringify(body) : undefined,
  });
}

async function del<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'DELETE' });
}

// ─── Error class ────────────────────────────────────────────────────

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

// ─── Types ──────────────────────────────────────────────────────────

export interface CompanyProfile {
  id: string;
  company_name: string;
  brand_guidelines: string;
  brand_tone?: string;
  reference_image_urls: string[];
  default_linkedin_account_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Campaign {
  id: string;
  name: string;
  state: string;
  goals: Record<string, unknown>;
  target_audience: Record<string, unknown>;
  platforms: string[];
  schedule: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  company_profile_id?: string;
  created_at: string;
  updated_at: string;
  version?: number;
}

export interface CampaignListResponse {
  campaigns: Campaign[];
  total: number;
  page: number;
  page_size: number;
}

export interface CampaignAsset {
  id: string;
  campaign_id: string;
  asset_type: string;
  content: Record<string, unknown>;
  source: string;
  storage_path?: string;
  created_at: string;
}

export interface GuestProfile {
  full_name: string;
  current_position?: string;
  organization?: string;
  professional_biography?: string;
  areas_of_expertise?: string[];
  confidence_level?: string;
}

export interface GuestSearchResponse {
  profile?: GuestProfile;
  needs_manual_input: boolean;
  error?: string;
}

export interface HealthStatus {
  status: string;
}

export interface CampaignImageResponse {
  image_url: string;
  model: string;
  generation_time_ms: number;
  fallback_used: boolean;
  brand_applied: boolean;
  validation: { width: number; height: number; passed: boolean };
}

export interface WorkflowStatus {
  thread_id?: string;
  workflow_id?: string;
  status: string;
}

// ─── Company API (10/10) ──────────────────────────────────────────────────────

export const companyApi = {
  /** POST /api/company */
  create: (data: { company_name: string; brand_guidelines: string; brand_tone?: string }) =>
    post<CompanyProfile>('/company', data),

  /** GET /api/company */
  list: () => get<CompanyProfile[]>('/company'),

  /** GET /api/company/{id} */
  get: (id: string) => get<CompanyProfile>(`/company/${id}`),

  /** PUT /api/company/{id} */
  update: (id: string, data: Partial<CompanyProfile>) =>
    put<CompanyProfile>(`/company/${id}`, data),

  /** PATCH /api/company/{id} */
  setLinkedInAccount: (companyId: string, accountId: string | null) =>
    patch<CompanyProfile>(`/company/${companyId}`, { default_linkedin_account_id: accountId }),

  /** DELETE /api/company/{id} */
  delete: (id: string) => del<void>(`/company/${id}`),

  /** GET /api/company/{id}/brand-info */
  getBrandInfo: (id: string) => get<Record<string, unknown>>(`/company/${id}/brand-info`),

  /** POST /api/company/{id}/brand-images  (multipart upload) */
  uploadImages: async (id: string, files: File[]) => {
    const formData = new FormData();
    files.forEach((f) => formData.append('images', f));
    const token = getActiveAccessToken();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${BASE_URL}/company/${id}/brand-images`, {
      method: 'POST',
      body: formData,
      headers,
    });
    if (!res.ok) {
      const json = await res.json();
      throw new ApiError(res.status, json.message || 'Upload failed', json);
    }
    const json = await res.json();
    return (json.data ?? json) as { urls: string[]; failed: { file: string; error: string }[]; total: number };
  },

  /** DELETE /api/company/{id}/brand-images/{index} */
  removeImage: (id: string, index: number) =>
    del<{ removed: boolean; remaining: number }>(`/company/${id}/brand-images/${index}`),

  /** POST /api/company/{id}/brand-images/{index}/replace  (multipart) */
  replaceImage: async (id: string, index: number, file: File) => {
    const formData = new FormData();
    formData.append('image', file);
    const token = getActiveAccessToken();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${BASE_URL}/company/${id}/brand-images/${index}/replace`, {
      method: 'POST',
      body: formData,
      headers,
    });
    if (!res.ok) {
      const json = await res.json();
      throw new ApiError(res.status, json.message || 'Replace failed', json);
    }
    const json = await res.json();
    return (json.data ?? json) as { url: string; index: number; total: number };
  },

  /** PUT /api/company/{id}/brand-images/reorder */
  reorderImages: (id: string, order: number[]) =>
    put<{ reordered: boolean; total: number }>(`/company/${id}/brand-images/reorder`, { order }),
};

// ─── Campaign API (11/11) ─────────────────────────────────────────────────────

export const campaignApi = {
  /** POST /api/campaigns */
  create: (data: {
    name: string;
    goals: {
      primary: string;            // required, min_length=1
      metrics?: string[];
      targets?: Record<string, unknown>;
    };
    target_audience: {
      segments?: string[];
      demographics?: Record<string, unknown>;
      interests?: string[];
    };
    platforms: string[];          // required, min_items=1
    schedule: {
      start_date: string;         // ISO datetime string
      end_date: string;           // ISO datetime string
      timezone: string;           // required, min_length=1
      recurrence_rule?: string;
    };
    company_profile_id?: string;
    metadata?: Record<string, unknown>;
  }) => post<Campaign>('/campaigns', data),

  /** GET /api/campaigns */
  list: (params?: { state?: string; page?: number; page_size?: number; company_profile_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.state) qs.set('state', params.state);
    if (params?.page) qs.set('page', String(params.page));
    if (params?.page_size) qs.set('page_size', String(params.page_size));
    if (params?.company_profile_id) qs.set('company_profile_id', params.company_profile_id);
    const query = qs.toString() ? `?${qs.toString()}` : '';
    return get<CampaignListResponse>(`/campaigns${query}`);
  },

  /** GET /api/campaigns/{id} */
  get: (id: string) => get<Campaign>(`/campaigns/${id}`),

  /** PUT /api/campaigns/{id} — requires If-Match header with current version number */
  update: (id: string, version: number, data: Partial<Campaign>) =>
    put<Campaign>(`/campaigns/${id}`, data, { 'If-Match': String(version) }),

  /** DELETE /api/campaigns/{id} */
  delete: (id: string) => del<void>(`/campaigns/${id}`),

  /** POST /api/campaigns/{id}/transition */
  transition: (id: string, to_state: string, reason?: string) =>
    post<Campaign>(`/campaigns/${id}/transition`, { to_state, reason }),

  /** POST /api/campaigns/{id}/archive */
  archive: (id: string, reason?: string) =>
    post<Campaign>(`/campaigns/${id}/archive`, reason ? { reason } : undefined),

  /** POST /api/campaigns/{id}/restore */
  restore: (id: string) => post<Campaign>(`/campaigns/${id}/restore`),

  /** GET /api/campaigns/{id}/history */
  history: (id: string, page = 1, page_size = 50) =>
    get<{ history: unknown[]; total: number; page: number; page_size: number }>(
      `/campaigns/${id}/history?page=${page}&page_size=${page_size}`
    ),

  /** POST /api/campaigns/{id}/assets */
  createAsset: (
    id: string,
    data: { asset_type: string; content: Record<string, unknown>; source: string; storage_path?: string }
  ) => post<CampaignAsset>(`/campaigns/${id}/assets`, data),

  /** GET /api/campaigns/{id}/assets */
  listAssets: (id: string) =>
    get<{ assets: CampaignAsset[]; total: number }>(`/campaigns/${id}/assets`),

  /** GET /api/campaigns/{id}/posts */
  getPosts: (id: string) =>
    get<
      Array<{
        id: string;
        campaign_id: string;
        slot_id?: string;
        hook?: string;
        body?: string;
        cta_text?: string;
        full_content?: string;
        status?: string;
        scheduled_at?: string;
        created_at?: string;
        media_type?: string;
        media_url?: string;
        unipile_post_id?: string;
        published_at?: string;
        linkedin_account_id?: string;
        timezone?: string;
      }>
    >(`/campaigns/${id}/posts`),
};

// ─── Validation API (2/2) ─────────────────────────────────────────────────────

export const validationApi = {
  /** POST /api/campaigns/{id}/validate */
  validate: (campaignId: string, data: { text_content: string; platform: string; image_url?: string }) =>
    post<Record<string, unknown>>(`/campaigns/${campaignId}/validate`, data),

  /** GET /api/campaigns/{id}/preview/check */
  previewCheck: (campaignId: string, params: { text_content: string; platform: string; image_url?: string }) => {
    const qs = new URLSearchParams({ text_content: params.text_content, platform: params.platform });
    if (params.image_url) qs.set('image_url', params.image_url);
    return get<{ campaign_id: string; can_preview: boolean; status: string; message: string }>(
      `/campaigns/${campaignId}/preview/check?${qs.toString()}`
    );
  },
};

// ─── Guest API (1/1) ─────────────────────────────────────────────────────────

export const guestApi = {
  /** POST /api/guest/search */
  search: (guest_name: string, company_name?: string) =>
    post<GuestSearchResponse>('/guest/search', { guest_name, company_name }),
};

// ─── Campaign Images API (1/1) ────────────────────────────────────────────────

export const campaignImagesApi = {
  /** POST /api/campaign-images */
  generate: (data: {
    company_profile_id: string;
    campaign_prompt: string;
    campaign_context?: Record<string, unknown>;
  }) => post<CampaignImageResponse>('/campaign-images', data),
};

// ─── AI Generation API (7/7) ─────────────────────────────────────────────────

export const aiApi = {
  /** POST /api/generate */
  generate: (context: {
    campaign_context: Record<string, unknown>;
    company_profile: Record<string, unknown>;
    audience: Record<string, unknown>;
    platforms: string[];
    brand_guidelines: Record<string, unknown>;
    reference_materials: Record<string, unknown>[];
    user_intent?: Record<string, unknown>;
  }) => post<{ artifacts: Record<string, unknown> }>('/generate', context),

  /** POST /api/regenerate/text */
  regenerateText: (existing_context: Record<string, unknown>, user_instructions?: Record<string, unknown>) =>
    post<{ artifacts: Record<string, unknown> }>('/regenerate/text', {
      existing_context,
      user_instructions,
    }),

  /** POST /api/regenerate/strategy */
  regenerateStrategy: (context: {
    campaign_context: Record<string, unknown>;
    company_profile: Record<string, unknown>;
    audience: Record<string, unknown>;
    platforms: string[];
    brand_guidelines: Record<string, unknown>;
    reference_materials: Record<string, unknown>[];
  }) => post<{ artifacts: Record<string, unknown> }>('/regenerate/strategy', context),

  /** POST /api/regenerate/image */
  regenerateImage: (existing_context: Record<string, unknown>, user_instructions?: Record<string, unknown>) =>
    post<{ artifacts: Record<string, unknown> }>('/regenerate/image', {
      existing_context,
      user_instructions,
    }),

  /** POST /api/validate */
  validate: (artifacts: Record<string, unknown>) =>
    post<{ validation: Record<string, unknown> }>('/validate', { artifacts }),

  /** POST /api/health (ai generation health) */
  health: () => post<{ status: string }>('/health'),

  /** GET /api/info */
  info: () => get<Record<string, unknown>>('/info'),
};

// ─── Workflow API (4/4) ───────────────────────────────────────────────────────

export const workflowApi = {
  /** POST /api/workflows?workflow_type=...&campaign_id=... */
  execute: (workflow_type: string, campaign_id: string) =>
    post<WorkflowStatus>(`/workflows?workflow_type=${encodeURIComponent(workflow_type)}&campaign_id=${encodeURIComponent(campaign_id)}`),

  /** GET /api/workflows/{thread_id} */
  getStatus: (thread_id: string) => get<WorkflowStatus>(`/workflows/${thread_id}`),

  /** POST /api/workflows/{thread_id}/approve */
  approve: (thread_id: string) => post<WorkflowStatus>(`/workflows/${thread_id}/approve`),

  /** POST /api/workflows/{thread_id}/reject */
  reject: (thread_id: string) => post<WorkflowStatus>(`/workflows/${thread_id}/reject`),
};

// ─── Image Processing API (1/1) ───────────────────────────────────────────────

export const imageProcessingApi = {
  /** POST /api/image-processing/validate */
  validate: (image_url: string) =>
    post<{ url: string; valid: boolean }>('/image-processing/validate', { image_url }),
};

// ─── Operations API (2/2) ─────────────────────────────────────────────────────

export const operationsApi = {
  /** GET /api/operations/metrics */
  getMetrics: () => get<{ metrics: Record<string, unknown> }>('/operations/metrics'),

  /** GET /api/operations/history */
  getHistory: () => get<{ history: unknown[] }>('/operations/history'),
};

// ─── Health API (3/3) ────────────────────────────────────────────────────────

export const healthApi = {
  /** GET /api/health */
  check: () => get<HealthStatus>('/health'),

  /** GET /api/ready */
  ready: () => get<HealthStatus>('/ready'),

  /** GET /api/live */
  live: () => get<HealthStatus>('/live'),
};
// ─── Plan API (7/7) ──────────────────────────────────────────────────────────

export interface PlanSection {
  [key: string]: unknown;
}

export interface CampaignPlanDocument {
  plan_id?: string;
  campaign_id?: string;
  campaign_name?: string;
  campaign_type?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  source_brief?: any;
  version?: number;
  language?: string;
  status?: string;
  approved?: boolean;
  title?: string;
  executive_summary?: string;
  core_strategy?: {
    objective?: string;
    smart_goals?: Array<{ goal: string; metric: string; target: string; deadline: string }>;
    personas?: Array<{ name: string; description: string; demographics: string; motivations: string[]; pain_points: string[]; where_they_are: string[] }>;
    positioning_statement?: string;
    unique_selling_proposition?: string;
    messaging_pillars?: string[];
    tone_of_voice?: string;
    objection_handling?: Array<{ objection: string; response: string }>;
  };
  channel_plan?: {
    platforms?: Array<{ platform: string; rationale: string; content_formats: string[]; posting_cadence: string; tone_adjustment: string; hashtag_strategy: string }>;
    phases?: Array<{ phase: string; duration: string; objective: string; key_message: string; primary_cta: string }>;
    calendar_slots?: Array<{ slot_id: string; date: string; platform: string; phase: string; theme: string; format_type: string; messaging_pillar: string; cta: string }>;
    overall_cadence?: string;
  };
  measurement?: {
    kpis?: Array<{ name: string; funnel_stage: string; target: string; measurement_method: string }>;
    tracking_plan?: string;
    reporting_cadence?: string;
    definition_of_success?: string;
  };
  competitive?: {
    landscape?: Array<{ name: string; positioning: string; strengths: string[]; weaknesses: string[]; source_url: string }>;
    differentiation_angle?: string;
    whitespace_opportunities?: string[];
  };
  schedule_plan?: {
    frequency?: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    slots?: any[];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    [key: string]: any;
  };
  research_status?: string;
  research_status_reason?: string;
  generated_at?: string;
}

export interface PlanMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  language: string;
  sections_targeted: string[];
  resulting_version?: number;
  created_at?: string;
}

export interface PlanVersion {
  version: number;
  change_summary: string;
  sections_changed: string[];
  created_at?: string;
}

export interface DraftPlanRequest {
  user_goal?: string;
  company_name?: string;
  brand_tone?: string;
  brand_guidelines?: string;
  event_name?: string;
  event_date?: string;
  venue?: string;
  registration_link?: string;
  platforms?: string[];
  guests?: string[];
  language?: string;
}

export const planApi = {
  /** POST /api/campaigns/{id}/plan/draft */
  draft: (campaignId: string, body: DraftPlanRequest) =>
    post<CampaignPlanDocument>(`/campaigns/${campaignId}/plan/draft`, body),

  /** GET /api/campaigns/{id}/plan */
  get: (campaignId: string) =>
    get<CampaignPlanDocument>(`/campaigns/${campaignId}/plan`),

  /** GET /api/campaigns/{id}/plan/versions */
  listVersions: (campaignId: string) =>
    get<PlanVersion[]>(`/campaigns/${campaignId}/plan/versions`),

  /** GET /api/campaigns/{id}/plan/versions/{v} */
  getVersion: (campaignId: string, version: number) =>
    get<CampaignPlanDocument>(`/campaigns/${campaignId}/plan/versions/${version}`),

  /** GET /api/campaigns/{id}/plan/messages */
  getMessages: (campaignId: string) =>
    get<PlanMessage[]>(`/campaigns/${campaignId}/plan/messages`),

  /** POST /api/campaigns/{id}/plan/messages */
  sendMessage: (campaignId: string, content: string) =>
    post<{ plan: CampaignPlanDocument; reply: string; version: number }>(
      `/campaigns/${campaignId}/plan/messages`,
      { content }
    ),

  /** POST /api/campaigns/{id}/plan/approve */
  approve: (campaignId: string) =>
    post<{ plan_id: string; campaign_id: string; version: number; approved: boolean; status: string }>(
      `/campaigns/${campaignId}/plan/approve`
    ),
};

export interface LinkedInPostItem {
  id?: string;
  post_id?: string;
  slot_id?: string;
  scheduled_at?: string;
  hook?: string;
  body?: string;
  cta_text?: string;
  full_content?: string;
  evidence_ids?: string[];
  status?: 'draft' | 'scheduled' | 'published' | 'failed' | string;
  unipile_post_id?: string;
  published_at?: string;
  media_type?: string;
  media_url?: string;
  linkedin_account_id?: string;
  timezone?: string;
}

export interface OutreachSequenceItem {
  id?: string;
  campaign_id: string;
  step_invite_msg: string;
  step_value_msg: string;
  step_followup_msg: string;
  current_step?: number;
  status?: string;
}

export interface LaunchpadPreviewData {
  campaign_id: string;
  posts: LinkedInPostItem[];
  outreach_sequence?: OutreachSequenceItem | null;
  autopilot_config: {
    daily_invite_limit: number;
    daily_message_limit: number;
    delay_min_seconds: number;
    delay_max_seconds: number;
    withdraw_after_days: number;
    business_hours_start: number;
    business_hours_end: number;
    stop_on_reply: boolean;
    timezone: string;
  };
}

export const linkedinApi = {
  /** POST /api/linkedin/campaigns/{id}/generate */
  generate: (campaignId: string, researchBriefDict?: Record<string, unknown>) =>
    post<{
      status: string;
      posts_generated: number;
      sequence_generated: boolean;
      posts?: Array<{
        id?: string;
        post_id?: string;
        hook?: string;
        body?: string;
        cta_text?: string;
        full_content?: string;
        content?: string;
      }>;
    }>(
      `/linkedin/campaigns/${campaignId}/generate`,
      { research_brief_dict: researchBriefDict }
    ),

  /** GET /api/linkedin/campaigns/{id}/preview */
  getPreview: (campaignId: string) =>
    get<LaunchpadPreviewData>(`/linkedin/campaigns/${campaignId}/preview`),

  /** PATCH /api/linkedin/campaigns/{id}/posts/{postId} */
  patchPost: (
    campaignId: string,
    postId: string,
    data: { hook?: string; body?: string; cta_text?: string; scheduled_at?: string; timezone?: string }
  ) =>
    patch<LinkedInPostItem>(`/linkedin/campaigns/${campaignId}/posts/${postId}`, data),

  /** POST /api/linkedin/campaigns/{id}/launch */
  launch: (campaignId: string, accountId: string) =>
    post<{ status: string; campaign_id: string; account_id: string; message: string }>(
      `/linkedin/campaigns/${campaignId}/launch`,
      { account_id: accountId }
    ),

  /** GET /api/linkedin/campaigns/{id}/status */
  getStatus: (campaignId: string) =>
    get<{
      campaign_id: string;
      total_posts: number;
      posts_published: number;
      posts_scheduled: number;
      total_outreach_leads: number;
      connected_leads: number;
      replied_leads: number;
    }>(`/linkedin/campaigns/${campaignId}/status`),

  /** POST /api/v1/linkedin/accounts/publish */
  publishPost: (text: string, accountId?: string) =>
    post<{ status: string; post_id: string; message: string }>('/linkedin/accounts/publish', {
      text,
      account_id: accountId,
    }),

  /** GET /api/v1/linkedin/connections */
  listConnections: (verify = false) =>
    get<LinkedInConnectedAccount[]>(`/linkedin/connections${verify ? '?verify=true' : ''}`),

  /** POST /api/v1/linkedin/connections/link */
  createConnectionLink: () =>
    post<{ url: string }>('/linkedin/connections/link'),

  /** POST /api/linkedin/campaigns/{id}/posts/{postId}/schedule */
  schedulePost: (campaignId: string, postId: string, scheduledAt: string, timezone?: string) =>
    post<LinkedInPostItem>(`/linkedin/campaigns/${campaignId}/posts/${postId}/schedule`, {
      scheduled_at: scheduledAt,
      timezone: timezone || 'UTC',
    }),

  /** POST /api/linkedin/campaigns/{id}/posts/{postId}/reschedule */
  reschedulePost: (campaignId: string, postId: string, scheduledAt: string, timezone?: string) =>
    post<LinkedInPostItem>(`/linkedin/campaigns/${campaignId}/posts/${postId}/reschedule`, {
      scheduled_at: scheduledAt,
      timezone: timezone || 'UTC',
    }),

  /** POST /api/linkedin/campaigns/{id}/posts/{postId}/cancel-schedule */
  cancelSchedule: (campaignId: string, postId: string) =>
    post<LinkedInPostItem>(`/linkedin/campaigns/${campaignId}/posts/${postId}/cancel-schedule`),

  /** POST /api/v1/linkedin/campaigns/{campaign_id}/generate/stream */
  generateStream: async (
    campaignId: string,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onEvent: (event: any) => void,
    researchBriefDict?: Record<string, unknown>
  ): Promise<void> => {
    const token = getActiveAccessToken();
    const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
    const res = await fetch(`${BASE_URL}/linkedin/campaigns/${campaignId}/generate/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders,
      },
      body: JSON.stringify({ research_brief_dict: researchBriefDict }),
    });
    if (!res.ok) {
      throw new Error(`Failed to generate stream: ${res.statusText}`);
    }
    const reader = res.body?.getReader();
    if (!reader) return;
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onEvent(data);
          } catch {
            // ignore
          }
        }
      }
    }
  },
};

export interface LinkedInConnectedAccount {
  id: string;
  user_id: string;
  unipile_account_id: string;
  account_name?: string | null;
  account_email?: string | null;
  provider: string;
  status: 'connected' | 'disconnected' | 'error';
  created_at: string;
  updated_at: string;
}

export type LinkedInAccount = LinkedInConnectedAccount;

export const linkedinAccountsApi = {
  list: (verify = false) => linkedinApi.listConnections(verify),
};

export interface IntakeChecklistState {
  campaign_name?: string | null;
  campaign_type?: string | null;
  event_name?: string | null;
  event_date?: string | null;
  venue?: string | null;
  has_guest?: boolean | null;
  guest_name?: string | null;
  guest_title?: string | null;
  guest_confirmed?: boolean;
  curriculum_breakdown?: string | null;
  outcome_deliverable?: string | null;
  is_free_or_paid?: string | null;
  registration_link?: string | null;
  target_audience?: string | null;
  audience_profile?: string | { summary?: string; [key: string]: unknown } | null;
  objective?: string | null;
  value_proposition?: string | null;
  cta_url?: string | null;
  category?: string | null;
}

export interface IntakeChatResponseData {
  campaign_id: string;
  reply: string;
  language: string;
  checklist: IntakeChecklistState;
  is_complete: boolean;
  guest_confirmation_needed: boolean;
  guest_detected?: { name: string; title: string } | null;
}

export const intakeApi = {
  /** POST /api/campaigns/intake/chat */
  sendMessage: (campaignId: string, userMessage: string, language: string = 'en') =>
    post<IntakeChatResponseData>('/campaigns/intake/chat', {
      campaign_id: campaignId,
      user_message: userMessage,
      language,
    }),

  /** GET /api/campaigns/intake/{campaign_id}/history */
  getHistory: (campaignId: string) =>
    get<{
      campaign_id: string;
      history: Array<{ id: string; role: 'user' | 'assistant' | 'system'; content: string; language: string; created_at: string }>;
      checklist: IntakeChecklistState;
      is_complete: boolean;
    }>(`/campaigns/intake/${campaignId}/history`),

  /** POST /api/campaigns/intake/confirm-guest */
  confirmGuest: (campaignId: string, guestName: string, guestTitle?: string, confirmed: boolean = true) =>
    post<{
      status: string;
      campaign_id: string;
      checklist: IntakeChecklistState;
      is_complete: boolean;
    }>('/campaigns/intake/confirm-guest', {
      campaign_id: campaignId,
      guest_name: guestName,
      guest_title: guestTitle,
      confirmed,
    }),

  /** DELETE /api/campaigns/intake/{campaign_id} */
  resetSession: (campaignId: string) =>
    del<{ status: string; message: string }>(`/campaigns/intake/${campaignId}`),

  /** POST /api/campaigns/intake/migrate — re-key checklist from session UUID to real campaign ID */
  migrateSession: (sessionId: string, campaignId: string) =>
    post<{ status: string; session_id: string; campaign_id: string; event_name?: string; guest_name?: string }>(
      '/campaigns/intake/migrate',
      { session_id: sessionId, campaign_id: campaignId }
    ),
};

// ─── Video API (1/1) ───────────────────────────────────────────────────────

export const videoApi = {
  /** POST /api/campaigns/{id}/video */
  generate: (campaignId: string, prompt?: string) =>
    post<{
      video_url: string;
      scenes: unknown[];
      asset?: CampaignAsset;
      draft_post?: LinkedInPostItem;
    }>(`/campaigns/${campaignId}/video`, prompt ? { prompt } : undefined),
};

// ─── Autopilot API ─────────────────────────────────────────────────────────

export interface AutopilotSettings {
  company_profile_id?: string;
  linkedin_account_id?: string | null;
  connected_account?: LinkedInConnectedAccount | null;
  engagement_enabled: boolean;
  auto_like_enabled: boolean;
  auto_comment_generation_enabled: boolean;
  auto_connect_enabled: boolean;
  likes_per_day: number;
  comments_per_day: number;
  invites_per_day: number;
  connection_note_template: string;
  timezone: string;
  // Legacy aliases
  master_active?: boolean;
  daily_connections?: number;
  daily_likes?: number;
  daily_comments?: number;
  post_time_slot?: string;
  video_time_slot?: string;
}

export interface EngagementActivityEvent {
  id: string;
  user_id: string;
  company_profile_id: string;
  linkedin_account_id: string;
  action_type: 'like' | 'comment' | 'connection_request';
  target_post_id?: string | null;
  target_profile_id?: string | null;
  review_queue_id?: string | null;
  comment_text?: string | null;
  status: 'claimed' | 'succeeded' | 'failed' | 'needs_review';
  provider_result_id?: string | null;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export const autopilotApi = {
  /** GET /api/v1/autopilot/settings */
  getSettings: (companyProfileId?: string) =>
    get<AutopilotSettings>(
      `/autopilot/settings${companyProfileId ? `?company_profile_id=${encodeURIComponent(companyProfileId)}` : ''}`
    ),

  /** PUT /api/v1/autopilot/settings */
  saveSettings: (settings: Partial<AutopilotSettings> & { company_profile_id?: string }) =>
    put<AutopilotSettings>('/autopilot/settings', settings),

  /** POST /api/v1/autopilot/toggle */
  toggle: (active: boolean, companyProfileId?: string) =>
    post<{ status: string; master_active: boolean; company_profile_id?: string }>(
      '/autopilot/toggle',
      { active, company_profile_id: companyProfileId }
    ),

  /** GET /api/v1/autopilot/tracker */
  getTracker: (companyProfileId?: string) =>
    get<{
      master_active: boolean;
      company_profile_id?: string;
      daily_progress: {
        connections_sent: number;
        connections_max: number;
        likes_given: number;
        likes_max: number;
        comments_posted: number;
        comments_max: number;
      };
      upcoming_queue: Array<{
        id: string;
        type: 'video' | 'post';
        title: string;
        scheduled_time: string;
        status: string;
      }>;
      running_campaigns: Array<{
        campaign_id: string;
        campaign_name: string;
        status: string;
        last_action: string;
        progress_pct: number;
      }>;
    }>(
      `/autopilot/tracker${companyProfileId ? `?company_profile_id=${encodeURIComponent(companyProfileId)}` : ''}`
    ),

  /** GET /api/v1/autopilot/activity */
  getActivity: (companyProfileId?: string, limit = 50) =>
    get<{
      events: EngagementActivityEvent[];
      total: number;
      company_profile_id: string;
    }>(
      `/autopilot/activity?limit=${limit}${companyProfileId ? `&company_profile_id=${encodeURIComponent(companyProfileId)}` : ''}`
    ),

  /** DELETE /api/v1/autopilot/queue/{id} */
  deleteQueueItem: (id: string) =>
    del<{
      success: boolean;
      id: string;
      deleted_from_db: boolean;
      message: string;
    }>(`/autopilot/queue/${id}`),

  /** POST /api/v1/autopilot/publish-now/{post_id} */
  publishNow: (postId: string) =>
    post<{
      success: boolean;
      status?: string;
      post_id?: string;
      unipile_post_id?: string;
      published_at?: string;
      linkedin_account_id?: string;
      error?: string;
      message?: string;
      post?: Record<string, unknown>;
    }>(`/autopilot/publish-now/${postId}`),

  /** GET /api/v1/autopilot/publisher-status */
  getPublisherStatus: () =>
    get<{
      total_posts: number;
      by_status: Record<string, number>;
      overdue_count: number;
      overdue_posts: Array<{ id: string; scheduled_at: string }>;
    }>('/autopilot/publisher-status'),
};

// ─── Personas API ─────────────────────────────────────────────────────────

export interface TargetPersona {
  id: string;
  user_id?: string;
  company_profile_id?: string;
  label: string;
  search_keywords: string;
  max_profiles: number;
  is_active: boolean;
  created_at: string;
}

export const personasApi = {
  /** GET /api/v1/autopilot/personas */
  list: (companyProfileId?: string) =>
    get<{ personas: TargetPersona[]; total: number; company_profile_id?: string }>(
      `/autopilot/personas${companyProfileId ? `?company_profile_id=${encodeURIComponent(companyProfileId)}` : ''}`
    ),

  /** POST /api/v1/autopilot/personas */
  create: (data: { company_profile_id?: string; label: string; search_keywords: string; max_profiles?: number }) =>
    post<{ success: boolean; persona?: TargetPersona }>('/autopilot/personas', data),

  /** PUT /api/v1/autopilot/personas/{id}?company_profile_id={brand_id} */
  update: (
    id: string,
    data: { label?: string; search_keywords?: string; max_profiles?: number; is_active?: boolean },
    companyProfileId: string
  ) =>
    put<{ success: boolean; persona?: TargetPersona }>(
      `/autopilot/personas/${id}?company_profile_id=${encodeURIComponent(companyProfileId)}`,
      data
    ),

  /** DELETE /api/v1/autopilot/personas/{id}?company_profile_id={brand_id} */
  delete: (id: string, companyProfileId: string) =>
    del<{ success: boolean; id: string }>(
      `/autopilot/personas/${id}?company_profile_id=${encodeURIComponent(companyProfileId)}`
    ),
};

// ─── Review Queue API ─────────────────────────────────────────────────────

export interface ReviewComment {
  id: string;
  user_id?: string;
  company_profile_id?: string;
  linkedin_account_id?: string;
  target_post_id: string;
  target_post_snippet: string;
  target_author_name: string;
  persona_label: string;
  generated_text: string;
  comment_text?: string;
  status: 'pending_review' | 'approved' | 'rejected' | 'published' | 'failed' | 'needs_review' | 'expired';
  reject_reason?: string;
  generated_at: string;
  reviewed_at?: string;
}

export const reviewQueueApi = {
  /** GET /api/v1/autopilot/review-queue */
  list: (companyProfileId?: string, statusFilter = 'pending_review') =>
    get<{ comments: ReviewComment[]; total: number }>(
      `/autopilot/review-queue?status_filter=${statusFilter}${companyProfileId ? `&company_profile_id=${encodeURIComponent(companyProfileId)}` : ''}`
    ),

  /** POST /api/v1/autopilot/review/{id}/approve */
  approve: (id: string, commentText?: string) =>
    post<{ success: boolean; comment_id: string; status: string; provider_result_id?: string; error?: string }>(
      `/autopilot/review/${id}/approve`,
      { comment_text: commentText }
    ),

  /** POST /api/v1/autopilot/review/{id}/reject */
  reject: (id: string, reason?: string) =>
    post<{ success: boolean; comment_id: string; status: string }>(
      `/autopilot/review/${id}/reject`,
      { reason }
    ),

  /** POST /api/v1/autopilot/review-queue/approve-all */
  approveAll: () =>
    post<{ success: boolean; approved_count: number }>('/autopilot/review-queue/approve-all'),
};

// ─── Circuit Breaker API ──────────────────────────────────────────────────

export const circuitBreakerApi = {
  /** GET /api/v1/autopilot/circuit-breaker */
  getStatus: (companyProfileId?: string) => {
    const q = companyProfileId ? `?company_profile_id=${encodeURIComponent(companyProfileId)}` : '';
    return get<{
      account_id?: string;
      state: string;
      tripped_at?: string | null;
      trip_reason?: string | null;
      cooldown_hours?: number;
      can_proceed?: boolean;
      message?: string;
    }>(`/autopilot/circuit-breaker${q}`);
  },

  /** POST /api/v1/autopilot/circuit-breaker/reset */
  reset: (companyProfileId?: string) => {
    const q = companyProfileId ? `?company_profile_id=${encodeURIComponent(companyProfileId)}` : '';
    return post<{ success: boolean; new_state: string; message: string }>(`/autopilot/circuit-breaker/reset${q}`);
  },
};


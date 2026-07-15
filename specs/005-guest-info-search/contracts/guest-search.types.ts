// TypeScript types for Guest Information Retrieval API

export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";

export interface SearchResult {
  website_name: string;
  page_title: string;
  snippet: string;
  source_url: string;
}

export interface GuestProfile {
  full_name: string;
  current_position: string;
  organization: string;
  professional_biography: string;
  areas_of_expertise: string[];
  confidence_level: ConfidenceLevel;
  sources_used: SearchResult[];
}

export interface GuestSearchRequest {
  guest_name: string;
  company_name?: string;
  session_id?: string;
}

export interface GuestSearchResponse {
  profile: GuestProfile;
  needs_manual_input: boolean;
  error?: string;
}

/** Error response from the API */
export interface ApiError {
  detail: string;
  error_code?: string;
}

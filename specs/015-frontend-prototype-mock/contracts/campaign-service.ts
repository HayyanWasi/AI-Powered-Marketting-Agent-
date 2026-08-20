// Campaign Service Interface
// This is the contract that mock AND future API implementations must satisfy.
// UI components depend only on this interface — never on mock implementations.

export interface Campaign {
  id: string
  title: string
  createdAt: Date
  updatedAt: Date
  prompts: Prompt[]
  assets: CampaignAsset[]
  concepts: CampaignConcept[]
  activeCompanyId: string | null
  status: 'idle' | 'generating' | 'complete'
}

export interface Prompt {
  id: string
  conversationId: string
  content: string
  timestamp: Date
}

export interface CampaignAsset {
  id: string
  conversationId: string
  type: 'headline' | 'body' | 'caption' | 'image' | 'cta'
  content: string
  label: string
  createdAt: Date
  metadata: Record<string, unknown>
}

export interface CampaignConcept {
  id: string
  conversationId: string
  assets: CampaignAsset[]
  promptId: string
  generatedAt: Date
}

export interface CampaignService {
  createConversation(): Promise<Campaign>
  getConversation(id: string): Promise<Campaign>
  listConversations(): Promise<Campaign[]>
  submitPrompt(conversationId: string, content: string): Promise<CampaignConcept>
  getAssets(conversationId: string): Promise<CampaignAsset[]>
}

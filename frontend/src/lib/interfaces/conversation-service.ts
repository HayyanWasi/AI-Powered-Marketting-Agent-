// Conversation service interface
// Contract that conversation service implementations must satisfy.

export interface Prompt {
  id: string
  conversationId: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export interface Conversation {
  id: string
  title: string
  createdAt: Date
  updatedAt: Date
  prompts: Prompt[]
  conversationId?: string
  status: 'idle' | 'generating' | 'complete'
}

export interface ConversationService {
  createConversation(): Promise<Conversation>
  getConversation(id: string): Promise<Conversation | null>
  listConversations(): Promise<Conversation[]>
  submitPrompt(conversationId: string, content: string): Promise<Conversation>
  getAssets(conversationId: string): Promise<any[]>
}
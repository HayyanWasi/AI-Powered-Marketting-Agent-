"use client"

import React, { createContext, useContext, ReactNode } from 'react'

import { ConversationService } from '@/lib/interfaces/conversation-service'

export interface ConversationContextType {
  conversationService: ConversationService
}

export const ConversationContext = createContext<ConversationContextType | null>(null)

export function ConversationProvider({ children }: { children: ReactNode }) {
  const conversationService = {
    createConversation: async () => {
      const newConversation = {
        id: `conv_${Date.now()}`,
        title: `New Conversation ${new Date().toLocaleDateString()}`,
        createdAt: new Date(),
        updatedAt: new Date(),
        prompts: [],
        concepts: [],
        selectedConceptId: null,
        companyProfileId: null,
        status: 'idle',
      }

      const conversations = JSON.parse(localStorage.getItem('conversations') || '[]')
      conversations.push(newConversation)
      localStorage.setItem('conversations', JSON.stringify(conversations))

      return newConversation
    },
    getConversation: async (id: string) => {
      const conversations = JSON.parse(localStorage.getItem('conversations') || '[]')
      return conversations.find((c: any) => c.id === id) || null
    },
    listConversations: async () => {
      return JSON.parse(localStorage.getItem('conversations') || '[]')
    },
    submitPrompt: async (conversationId: string, content: string) => {
      const conversations = JSON.parse(localStorage.getItem('conversations') || '[]')
      const conversation = conversations.find((c: any) => c.id === conversationId)
      if (!conversation) throw new Error('Conversation not found')

      conversation.prompts = conversation.prompts || []
      conversation.prompts.push({
        id: `prompt_${Date.now()}`,
        content,
        timestamp: new Date().toISOString(),
        role: 'user'
      })
      conversation.updatedAt = new Date().toISOString()

      const updatedConversations = conversations.map((c: any) => c.id === conversationId ? conversation : c)
      localStorage.setItem('conversations', JSON.stringify(updatedConversations))
      return conversation
    }
  }

  return (
    <ConversationContext.Provider value={{ conversationService }}>
      {children}
    </ConversationContext.Provider>
  )
}

export function useConversationService() {
  const context = useContext<ConversationContextType | null>(ConversationContext)

  if (!context) {
    throw new Error('useConversationService must be used within a ConversationProvider')
  }

  return context.conversationService
}
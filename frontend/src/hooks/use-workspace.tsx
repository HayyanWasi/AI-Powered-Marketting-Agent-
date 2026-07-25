"use client"

import React, { createContext, useContext, ReactNode, useReducer, useState } from "react"

import { useConversationService } from "@/hooks/use-conversation"
import type { Conversation } from "@/lib/interfaces/conversation-service"

type WorkspaceState =
  | { mode: 'idle' }
  | { mode: 'generating'; stage: string; progress: number }
  | { mode: 'viewing-results'; stage: string; progress: number }
  | { mode: 'awaiting-prompt' }

type WorkspaceAction =
  | { type: 'SET_IDLE' }
  | { type: 'SET_GENERATING'; stage: string; progress: number }
  | { type: 'SET_VIEWING_RESULTS'; stage: string; progress: number }
  | { type: 'SET_AWAITING_PROMPT' }

export const WorkspaceContext = createContext<WorkspaceContextType | null>(null)

type WorkspaceContextType = {
  state: WorkspaceState
  activeConversationId: string | null
  setIdle: () => void
  setGenerating: (stage: string, progress: number) => void
  setViewingResults: (stage: string, progress: number) => void
  setAwaitingPrompt: () => void
  setActiveConversationId: (conversationId: string) => void
  submitPrompt: (content: string) => Promise<Conversation>
}

const initialState: WorkspaceState = { mode: 'idle' }

function workspaceReducer(state: WorkspaceState, action: WorkspaceAction): WorkspaceState {
  switch (action.type) {
    case 'SET_IDLE':
      return { mode: 'idle' }

    case 'SET_GENERATING':
      return { mode: 'generating', stage: action.stage, progress: action.progress }

    case 'SET_VIEWING_RESULTS':
      return { mode: 'viewing-results', stage: action.stage, progress: action.progress }

    case 'SET_AWAITING_PROMPT':
      return { mode: 'awaiting-prompt' }

    default:
      return state
  }
}

function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(workspaceReducer, initialState)
  const [activeConversationId, setActiveConversationIdState] = useState<string | null>(null)

  const conversationService = useConversationService()

  const setIdle = () => {
    dispatch({ type: 'SET_IDLE' })
  }

  const setGenerating = (stage: string, progress: number) => {
    dispatch({ type: 'SET_GENERATING', stage, progress })
  }

  const setViewingResults = (stage: string, progress: number) => {
    dispatch({ type: 'SET_VIEWING_RESULTS', stage, progress })
  }

  const setAwaitingPrompt = () => {
    dispatch({ type: 'SET_AWAITING_PROMPT' })
  }

  const setActiveConversationId = (conversationId: string) => {
    setActiveConversationIdState(conversationId)
  }

  const submitPrompt = async (content: string): Promise<Conversation> => {
    setGenerating('Preparing conversation', 0)

    let conversationId = activeConversationId
    if (!conversationId) {
      const created = await conversationService.createConversation()
      conversationId = created.id
      setActiveConversationId(conversationId)
    }

    setGenerating('Submitting prompt', 50)
    const updated = await conversationService.submitPrompt(conversationId, content)
    setViewingResults('Viewing results', 100)
    setAwaitingPrompt()

    return updated
  }

  const value: WorkspaceContextType = {
    state,
    activeConversationId,
    setIdle,
    setGenerating,
    setViewingResults,
    setAwaitingPrompt,
    setActiveConversationId,
    submitPrompt,
  }

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
}

function useWorkspace() {
  const context = useContext<WorkspaceContextType | null>(WorkspaceContext)

  if (!context) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider')
  }

  return context
}

export { WorkspaceProvider, useWorkspace, type WorkspaceState }

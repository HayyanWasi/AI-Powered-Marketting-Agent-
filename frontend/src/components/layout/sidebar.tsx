"use client"

import React from 'react'
import { cn } from '@/lib/utils'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ConversationList } from '@/components/chat/conversation-list'

export function Sidebar({
  conversations,
  profile,
  onNewConversation,
  onConversationSelect,
  isOpen,
}: {
  conversations: Conversation[]
  profile: any
  onNewConversation: () => void
  onConversationSelect: (id: string) => void
  isOpen: boolean
}) {
  return (
    <Card
      variant={isOpen ? 'default' : 'glassDark'}
      className={cn(
        'h-full overflow-hidden rounded-none border-0 md:rounded-xl md:border md:border-white/20',
        'flex flex-col backdrop-blur-xl',
        isOpen ? 'fixed inset-y-0 left-0 w-72' : 'hidden md:flex'
      )}
    >
      <div className="flex-shrink-0 p-6">
        <div className="mb-6 flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600" />
          <div>
            <h2 className="text-lg font-semibold">AI Marketing Agent</h2>
            <p className="text-sm text-muted-foreground">Version 1.0.0</p>
          </div>
        </div>

        <Button
          variant="glass"
          className="w-full"
          onClick={onNewConversation}
        >
          + New Conversation
        </Button>
      </div>

      {profile && (
        <div className="flex-shrink-0 border-t border-white/10 p-6">
          <h3 className="mb-3 text-sm font-medium">Company Profile</h3>
          <Card
            variant="glass"
            className="p-4"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{profile.companyName}</span>
                <Badge variant="secondary" className="text-xs">Active</Badge>
              </div>
              <p className="text-xs text-muted-foreground">{profile.industry}</p>
              <p className="text-xs text-muted-foreground line-clamp-2">
                {profile.brandDescription}
              </p>
            </div>
          </Card>
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        <ConversationList
          conversations={conversations}
          onSelect={onConversationSelect}
        />
      </div>
    </Card>
  )
}

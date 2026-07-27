"use client"

import React from "react"
import { cn } from "@/lib/utils"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { Conversation } from "@/lib/interfaces/conversation-service"

interface ConversationListProps {
  conversations: Conversation[]
  onSelect: (id: string) => void
  className?: string
}

export function ConversationList({
  conversations,
  onSelect,
  className,
}: ConversationListProps)
 {
  return (
    <div className={cn("space-y-2", className)}>
      <h3 className="px-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
        Recent Conversations
      </h3>
      {conversations.map((conversation) => (
        <Card
          key={conversation.id}
          variant="interactive"
          className="cursor-pointer p-3"
          onClick={() => onSelect(conversation.id)}
        >
          <div className="space-y-2">
            <div className="flex items-start justify-between">
              <h4 className="text-sm font-medium line-clamp-1">
                {conversation.title || `Conversation ${conversation.id.substring(0, 8)}`}
              </h4>
              <Badge variant="glass" className="text-xs">
                {conversation.status}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              {conversation.createdAt.toLocaleDateString()}
            </p>
          </div>
        </Card>
      ))}
      {conversations.length === 0 && (
        <div className="py-8 text-center text-sm text-muted-foreground">
          No conversations yet
        </div>
      )}
    </div>
  )
}

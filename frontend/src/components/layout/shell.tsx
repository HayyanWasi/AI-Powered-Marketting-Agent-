"use client"

import React, { useState } from 'react'
import { Menu, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export function Shell() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  const handleNewConversation = () => {
    setCurrentWorkspace('conversation')
    setIsSidebarOpen(false)
  }

  const handleConversationSelect = (conversationId: string) => {
    setCurrentWorkspace('conversation')
    setIsSidebarOpen(false)
  }

  return (
    <div className="relative min-h-screen bg-background text-foreground">
      <Button
        variant="glass"
        size="sm"
        className="fixed top-4 left-4 z-50 md:hidden"
        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
      >
        {isSidebarOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
      </Button>

      <div
        className={cn(
          'fixed inset-y-0 left-0 z-40 w-72 transform transition-transform duration-300 ease-in-out md:relative md:transform-none',
          isSidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        )}
      >
        <Sidebar
          conversations={[]}
          profile={null}
          onNewConversation={handleNewConversation}
          onConversationSelect={handleConversationSelect}
          isOpen={isSidebarOpen}
        />
      </div>

      <main
        className={cn(
          'md:ml-72 min-h-screen transition-all duration-300',
          'bg-gradient-to-br from-background via-background to-muted/20'
        )}
      >
        <Workspace currentWorkspace="prompt" />
      </main>

      {isSidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/20 backdrop-blur-sm md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}
    </div>
  )
}

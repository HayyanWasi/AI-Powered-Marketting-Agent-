"use client"

import React, { FormEvent } from 'react'
import { Send } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

interface PromptInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  disabled?: boolean
  placeholder?: string
  minHeight?: string
}

export function PromptInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder = "Describe your marketing campaign...",
  minHeight = "120px",
}: PromptInputProps) {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (value.trim() && !disabled) {
      onSubmit()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (value.trim() && !disabled) {
        onSubmit()
      }
    }
  }

  return (
    <Card
      variant="glass"
      className="relative overflow-hidden transition-all duration-200"
      style={{ minHeight }}
    >
      <form
        onSubmit={handleSubmit}
        className="flex h-full w-full flex-col p-4"
      >
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={placeholder}
          className="w-full resize-none border-0 bg-transparent text-base text-foreground placeholder:text-foreground/50 focus-visible:ring-0 focus-visible:ring-offset-0"
          style={{ minHeight: '60px' }}
        />

        <div className="mt-auto pt-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>Press Enter to submit</span>
            </div>

            <Button
              type="submit"
              variant="glass"
              size="sm"
              disabled={!value.trim() || disabled}
              className={cn(
                'transition-all duration-200',
                !value.trim() && 'opacity-50 cursor-not-allowed'
              )}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </form>
    </Card>
  )
}

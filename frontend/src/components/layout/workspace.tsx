"use client"

import React from 'react'
import { cn } from '@/lib/utils'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

export function Workspace({ currentWorkspace }: { currentWorkspace: 'prompt' | 'conversation' | 'company' }) {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="flex-shrink-0 border-b border-white/10 bg-background/80 p-6 backdrop-blur-md">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">
              {currentWorkspace === 'prompt' && 'Prompt Workspace'}
              {currentWorkspace === 'conversation' && 'Conversation'}
              {currentWorkspace === 'company' && 'Company Profile'}
            </h1>
            <p className="text-muted-foreground">
              {currentWorkspace === 'prompt' && 'Generate AI marketing campaigns through natural conversation'}
              {currentWorkspace === 'conversation' && 'Review and interact with campaign conversations'}
              {currentWorkspace === 'company' && 'Manage your company profile and brand information'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="glass" className="hidden md:inline-flex">
              Status: Running
            </Badge>
          </div>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-hidden p-6">
        {currentWorkspace === 'prompt' && (
          <div className="mx-auto max-w-4xl space-y-8">
            <Card variant="glass" className="p-8">
              <h2 className="mb-4 text-xl font-semibold">Start Your Campaign</h2>
              <p className="mb-6 text-muted-foreground">
                Describe your marketing campaign in natural language. Our AI will generate complete marketing materials including headlines, body copy, images, and calls-to-action.
              </p>
              <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Campaign Goal</label>
                    <input
                      placeholder="e.g., Increase brand awareness by 25%"
                      className="w-full rounded-md border border-white/20 bg-white/10 px-3 py-2 text-sm backdrop-blur-sm focus:border-white/40 focus:bg-white/20 focus:outline-none"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Target Audience</label>
                    <input
                      placeholder="e.g., Tech professionals age 25-45"
                      className="w-full rounded-md border border-white/20 bg-white/10 px-3 py-2 text-sm backdrop-blur-sm focus:border-white/40 focus:bg-white/20 focus:outline-none"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Campaign Description</label>
                  <textarea
                    placeholder="Tell us about your campaign..."
                    rows={4}
                    className="w-full resize-none rounded-md border border-white/20 bg-white/10 px-3 py-2 text-sm backdrop-blur-sm focus:border-white/40 focus:bg-white/20 focus:outline-none"
                  />
                </div>
                <Button variant="glass" className="w-full md:w-auto">
                  Generate Campaign
                </Button>
              </div>
            </Card>

            <div className="grid gap-6 md:grid-cols-2">
              <Card variant="glass" className="p-6">
                <h3 className="mb-3 text-lg font-medium">Quick Actions</h3>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>• Generate new campaigns from scratch</li>
                  <li>• Refine existing campaign outputs</li>
                  <li>• Create variations for different platforms</li>
                  <li>• A/B test campaign elements</li>
                </ul>
              </Card>
              <Card variant="glass" className="p-6">
                <h3 className="mb-3 text-lg font-medium">Recent Templates</h3>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>• Product Launch Campaign</li>
                  <li>• Brand Awareness Initiative</li>
                  <li>• Lead Generation Series</li>
                  <li>• Seasonal Promotion Pack</li>
                </ul>
              </Card>
            </div>
          </div>
        )}

        {currentWorkspace === 'conversation' && (
          <div className="space-y-6">
            <Card variant="glass" className="p-8">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold">Campaign Canvas</h2>
                  <Badge variant="success">Generated</Badge>
                </div>
                <div className="grid gap-6 md:grid-cols-2">
                  <div className="space-y-3">
                    <div className="h-32 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-600/20" />
                    <h3 className="font-medium">Generated Headline</h3>
                    <p className="text-sm text-muted-foreground">
                      "Reimagining Digital Horizons: Harnessing AI for Modern Marketing Success"
                    </p>
                  </div>
                  <div className="space-y-3">
                    <div className="h-32 rounded-lg bg-gradient-to-br from-green-500/20 to-teal-600/20" />
                    <h3 className="font-medium">Body Copy</h3>
                    <p className="text-sm text-muted-foreground">
                      Our cutting-edge approach leverages artificial intelligence to transform your marketing landscape into measurable growth opportunities.
                    </p>
                  </div>
                </div>
                <div className="pt-4">
                  <Button variant="glass">Refine Output</Button>
                </div>
              </div>
            </Card>
          </div>
        )}

        {currentWorkspace === 'company' && (
          <div className="mx-auto max-w-2xl space-y-6">
            <Card variant="glass" className="p-8">
              <h2 className="mb-6 text-xl font-semibold">Company Profile</h2>
              <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Company Name</label>
                    <input
                      placeholder="Acme Corporation"
                      className="w-full rounded-md border border-white/20 bg-white/10 px-3 py-2 text-sm backdrop-blur-sm focus:border-white/40 focus:bg-white/20 focus:outline-none"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Industry</label>
                    <input
                      placeholder="Technology"
                      className="w-full rounded-md border border-white/20 bg-white/10 px-3 py-2 text-sm backdrop-blur-sm focus:border-white/40 focus:bg-white/20 focus:outline-none"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Brand Description</label>
                  <textarea
                    placeholder="Describe your brand..."
                    rows={3}
                    className="w-full resize-none rounded-md border border-white/20 bg-white/10 px-3 py-2 text-sm backdrop-blur-sm focus:border-white/40 focus:bg-white/20 focus:outline-none"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Brand Voice</label>
                  <select className="w-full rounded-md border border-white/20 bg-white/10 px-3 py-2 text-sm backdrop-blur-sm focus:border-white/40 focus:bg-white/20 focus:outline-none">
                    <option>Professional</option>
                    <option>Friendly</option>
                    <option>Bold</option>
                    <option>Creative</option>
                  </select>
                </div>
                <Button variant="glass" className="w-full md:w-auto">Save Profile</Button>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}

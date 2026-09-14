"use client";

import { useState, useRef, useEffect } from "react";
import Navbar from "@/components/Navbar";
import {
  ChatMessage,
  LinkedInArtifact,
  CampaignStreamEvent,
} from "@/components/campaign/types";
import { streamCampaignResponse } from "@/components/campaign/apiAdapter";
import ChatInput from "@/components/campaign/ChatInput";
import AssistantMessageBubble from "@/components/campaign/AssistantMessageBubble";
import UserMessageBubble from "@/components/campaign/UserMessageBubble";
import ArtifactPanel from "@/components/campaign/ArtifactPanel";
import { Layers, Sparkles } from "lucide-react";

export default function NewCampaignPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);

  // Global Artifact State Tracking
  const [artifacts, setArtifacts] = useState<Record<string, LinkedInArtifact>>({});
  const [activeArtifactId, setActiveArtifactId] = useState<string | null>(null);
  const [isArtifactOpen, setIsArtifactOpen] = useState(false);

  // Floating mobile banner notification
  const [mobileBadgeNotice, setMobileBadgeNotice] = useState<string | null>(null);

  // Reference for internal chat scroll ONLY (prevents window scrolling down to footer)
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: messagesContainerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isGenerating]);

  const handleSendMessage = async (promptText: string) => {
    if (isGenerating) return;

    const userTimestamp = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: promptText,
      timestamp: userTimestamp,
    };

    const assistantId = `assistant-${Date.now()}`;
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      timestamp: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      thoughts: [],
      isThinking: true,
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setIsGenerating(true);

    let currentArtifactId: string | null = null;

    try {
      await streamCampaignResponse(promptText, (event: CampaignStreamEvent) => {
        switch (event.type) {
          case "thought":
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? {
                      ...msg,
                      thoughts: [...(msg.thoughts || []), event.step],
                    }
                  : msg
              )
            );
            break;

          case "content":
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? {
                      ...msg,
                      isThinking: false,
                      content: msg.content + event.chunk,
                    }
                  : msg
              )
            );
            break;

          case "artifact_start":
            currentArtifactId = event.id;
            setActiveArtifactId(event.id);

            // Open artifact side panel immediately
            setIsArtifactOpen(true);
            setMobileBadgeNotice("Strategy & Drafts Ready • Tap to view");

            setArtifacts((prev) => ({
              ...prev,
              [event.id]: {
                id: event.id,
                title: event.title,
                campaignGoal: event.campaignGoal,
                strategy: event.strategy,
                posts: [],
              },
            }));

            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? {
                      ...msg,
                      artifactId: event.id,
                    }
                  : msg
              )
            );
            break;

          case "artifact_strategy":
            if (currentArtifactId) {
              setArtifacts((prev) => {
                const existing = prev[currentArtifactId!];
                if (!existing) return prev;
                return {
                  ...prev,
                  [currentArtifactId!]: {
                    ...existing,
                    strategy: event.strategy,
                  },
                };
              });
            }
            break;

          case "artifact_post_add":
            if (currentArtifactId) {
              setArtifacts((prev) => {
                const existing = prev[currentArtifactId!];
                if (!existing) return prev;
                return {
                  ...prev,
                  [currentArtifactId!]: {
                    ...existing,
                    posts: [...existing.posts, event.post],
                  },
                };
              });
            }
            break;

          case "artifact_post_chunk":
            if (currentArtifactId) {
              setArtifacts((prev) => {
                const existing = prev[currentArtifactId!];
                if (!existing) return prev;
                return {
                  ...prev,
                  [currentArtifactId!]: {
                    ...existing,
                    posts: existing.posts.map((p) =>
                      p.id === event.postId
                        ? { ...p, content: p.content + event.chunk }
                        : p
                    ),
                  },
                };
              });
            }
            break;

          case "done":
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? {
                      ...msg,
                      isThinking: false,
                      isStreaming: false,
                      thoughtDuration: event.totalDuration,
                    }
                  : msg
              )
            );
            setIsGenerating(false);
            break;
        }
      });
    } catch {
      setIsGenerating(false);
    }
  };

  const handleViewArtifact = (id: string) => {
    setActiveArtifactId(id);
    setIsArtifactOpen(true);
    setMobileBadgeNotice(null);
  };

  const activeArtifact = activeArtifactId ? artifacts[activeArtifactId] || null : null;
  const isInitial = messages.length === 0;

  return (
    <div className="page-wrapper h-screen max-h-screen overflow-hidden selection:bg-[#d75dff]/30 selection:text-[#0e151c] flex flex-col bg-[#0e151c]">
      {/* Top Floating Navbar */}
      <Navbar />

      {/* Main Campaign Canvas - Viewport Locked to Prevent Any Window Scrolling */}
      <main className="pt-20 pb-3 px-3 sm:px-6 flex-1 flex flex-col relative overflow-hidden h-[calc(100vh-5rem)]">
        <div className="flex-1 rounded-[24px] bg-[#0E151C] text-white border border-[#272F38]/70 shadow-2xl relative overflow-hidden flex flex-col md:flex-row h-full">
          {/* Subtle Ambient Glows */}
          <div className="absolute top-10 left-1/4 w-[500px] h-[300px] bg-[#00c2ee]/5 blur-[140px] rounded-full pointer-events-none -z-10" />
          <div className="absolute top-1/2 right-10 w-[450px] h-[300px] bg-[#d75dff]/5 blur-[130px] rounded-full pointer-events-none -z-10" />

          {/* Left / Main Column: Chat Area */}
          <div
            className={`flex-1 flex flex-col relative h-full transition-all duration-300 ${
              isArtifactOpen ? "md:w-1/2" : "w-full"
            }`}
          >
            {/* Top Workspace Header Bar */}
            <div className="px-5 py-3 border-b border-white/[0.06] bg-[#121820]/90 flex items-center justify-between flex-shrink-0 z-10 backdrop-blur-md">
              <div className="flex items-center space-x-2.5">
                <div className="w-6 h-6 rounded-md bg-[#00c2ee]/10 border border-[#00c2ee]/20 text-[#00c2ee] flex items-center justify-center">
                  <Sparkles size={13} />
                </div>
                <span className="text-xs font-semibold text-[#F5F7FA]">AI Campaign Studio</span>
                {isGenerating && (
                  <span className="text-[11px] text-[#00c2ee] font-medium animate-pulse flex items-center space-x-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#00c2ee] inline-block" />
                    <span>Active processing...</span>
                  </span>
                )}
              </div>

              {/* Artifact Studio Panel Manual Toggle */}
              {activeArtifact && (
                <button
                  type="button"
                  onClick={() => setIsArtifactOpen(!isArtifactOpen)}
                  className="px-3 py-1.5 rounded-lg bg-[#18222D] hover:bg-[#202E3D] border border-[#273240] text-xs font-medium text-[#00c2ee] flex items-center space-x-1.5 transition-all cursor-pointer shadow-sm"
                >
                  <Layers size={13} />
                  <span>{isArtifactOpen ? "Hide Studio Panel" : "Open Studio Drafts"}</span>
                </button>
              )}
            </div>

            {/* Scrollable Messages Area - Scrolled internally via ref, NEVER scrolling the window */}
            <div
              ref={messagesContainerRef}
              className="flex-1 overflow-y-auto pt-4 pb-36 px-2 sm:px-4"
            >
              {messages.map((message) =>
                message.role === "user" ? (
                  <UserMessageBubble key={message.id} message={message} />
                ) : (
                  <AssistantMessageBubble
                    key={message.id}
                    message={message}
                    onViewArtifact={handleViewArtifact}
                  />
                )
              )}
            </div>

            {/* Mobile Floating Badge Notification (when artifact is ready on mobile) */}
            {mobileBadgeNotice && !isArtifactOpen && (
              <div className="md:hidden absolute bottom-24 left-1/2 -translate-x-1/2 z-30">
                <button
                  type="button"
                  onClick={() => {
                    setIsArtifactOpen(true);
                    setMobileBadgeNotice(null);
                  }}
                  className="px-4 py-2 rounded-full bg-gradient-to-r from-[#00c2ee] to-[#d75dff] text-black font-bold text-xs shadow-2xl flex items-center space-x-2 animate-bounce cursor-pointer"
                >
                  <Layers size={14} />
                  <span>{mobileBadgeNotice}</span>
                </button>
              </div>
            )}

            {/* Single Persistent ChatInput (Positioned dynamically from center to bottom) */}
            <div
              className={`absolute left-0 right-0 z-20 pointer-events-none transition-all duration-500 ease-in-out ${
                isInitial
                  ? "top-1/2 -translate-y-1/2"
                  : "bottom-4 translate-y-0"
              }`}
            >
              <div className="pointer-events-auto">
                <ChatInput
                  onSend={handleSendMessage}
                  disabled={isGenerating}
                  isInitial={isInitial}
                  onSelectPrompt={(p) => handleSendMessage(p)}
                />
              </div>
            </div>
          </div>

          {/* Right Column: Split-Screen Artifact Panel (LinkedIn Post Viewer) */}
          <ArtifactPanel
            artifact={activeArtifact}
            isOpen={isArtifactOpen}
            onClose={() => setIsArtifactOpen(false)}
            isGenerating={isGenerating}
          />
        </div>
      </main>
    </div>
  );
}

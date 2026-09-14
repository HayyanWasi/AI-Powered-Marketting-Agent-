"use client";

import { useState, useRef, useEffect } from "react";
import Navbar from "@/components/Navbar";
import VideoChatInput from "@/components/video/VideoChatInput";
import VideoStudioPanel from "@/components/video/VideoStudioPanel";
import ThoughtContainer from "@/components/campaign/ThoughtContainer";
import { useVideoGeneration } from "@/components/video/useVideoGeneration";
import { ThoughtStep } from "@/components/campaign/types";
import {
  Camera,
  Film,
  BarChart3,
  Sparkles,
} from "lucide-react";

interface VideoChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  thoughts?: ThoughtStep[];
}

const promptStarters = [
  {
    title: "Retail replenishment drone shot",
    desc: "Cinematic overhead view of automated stores.",
    icon: Camera,
    prompt:
      "Cinematic landscape drone shot over 1M+ retail stores automated by autonomous AI agents with physical depth of field.",
  },
  {
    title: "Product commercial",
    desc: "High-energy 16:9 commercial showing rapid ordering.",
    icon: Film,
    prompt:
      "High-energy 16:9 commercial showing FMCG mobile ordering in under 4 minutes with seamless motion interpolation.",
  },
  {
    title: "Enterprise sales analytics",
    desc: "Photorealistic scene of directors analyzing sales velocity.",
    icon: BarChart3,
    prompt:
      "Photorealistic commercial showcasing enterprise sales directors analyzing real-time order velocity across global distribution channels.",
  },
  {
    title: "Brand story teaser",
    desc: "Atmospheric cinematic lighting with slow camera pan.",
    icon: Sparkles,
    prompt:
      "Atmospheric cinematic lighting with slow landscape camera pan highlighting autonomous sales orchestration for Fortune 500 brands.",
  },
];

export default function VideoGenerationPage() {
  const [messages, setMessages] = useState<VideoChatMessage[]>([]);
  // Container-scoped scroll reference (never scrolls the entire window or jumps to footer)
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const {
    status,
    currentStage,
    displayProgress,
    error,
    artifact,
    startGeneration,
    selectVariation,
    updatePrompt,
    retry,
  } = useVideoGeneration();

  const scrollToBottom = () => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: messagesContainerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  };

  useEffect(() => {
    if (messages.length > 0) {
      scrollToBottom();
    }
  }, [messages, status]);

  const messageIdRef = useRef(0);

  const handleSendMessage = (promptText: string) => {
    if (status === "queued" || status === "generating") return;

    messageIdRef.current += 1;
    const userMsgId = `user-${messageIdRef.current}`;
    messageIdRef.current += 1;
    const assistantMsgId = `assistant-${messageIdRef.current}`;

    const userTimestamp = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    const userMessage: VideoChatMessage = {
      id: userMsgId,
      role: "user",
      content: promptText,
      timestamp: userTimestamp,
    };

    const initialThoughts: ThoughtStep[] = [
      {
        id: "v-step-1",
        title: "Analyzing prompt & scene dynamics...",
        detail: "16:9 Landscape aspect ratio locked at 1080p 60 FPS.",
        timestamp: userTimestamp,
      },
      {
        id: "v-step-2",
        title: "Synthesizing 16:9 neural keyframes...",
        detail: "Evaluating camera trajectory & foreground lighting passes.",
        timestamp: userTimestamp,
      },
      {
        id: "v-step-3",
        title: "Interpolating temporal motion & lighting...",
        detail: "Synthesizing optical physics and frame continuity.",
        timestamp: userTimestamp,
      },
    ];

    const assistantMessage: VideoChatMessage = {
      id: assistantMsgId,
      role: "assistant",
      content: `Rendering your 9:16 vertical Reel commercial for: "${promptText}". Live inference progress and previews are active in the Video Studio.`,
      timestamp: userTimestamp,
      thoughts: initialThoughts,
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    startGeneration(promptText);
  };

  const isGenerating = status === "queued" || status === "generating";

  return (
    <div className="page-wrapper h-screen max-h-screen overflow-hidden selection:bg-[#20B8E5]/30 selection:text-white flex flex-col bg-[#0E141B] font-sans">
      {/* Top Navbar */}
      <Navbar />

      {/* STATE 1: Initial Empty Hero State (No sidebar, no split-screen, perfectly centered) */}
      {messages.length === 0 ? (
        <main className="pt-20 pb-4 px-4 flex-1 flex flex-col items-center justify-center relative overflow-hidden h-[calc(100vh-5rem)]">
          <div className="max-w-3xl w-full mx-auto px-4 flex-1 flex flex-col justify-center items-center">
            <div className="flex flex-col items-center justify-center w-full max-w-2xl mx-auto text-center space-y-6 sm:space-y-8">
              {/* Heading Block */}
              <div className="space-y-2">
                <h1 className="text-2xl sm:text-3xl lg:text-4xl font-semibold text-[#F5F7FA] tracking-tight leading-tight">
                  What Reel commercial are we creating today?
                </h1>
                <p className="text-xs sm:text-sm text-[#9AA6B2] max-w-md mx-auto leading-relaxed">
                  Describe your scene, camera angle, and style. Hipoclipse AI will render a 9:16 vertical Reel for Instagram, TikTok, and Shorts.
                </p>
              </div>

              {/* 2x2 Grid of Video Prompt Starters */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 w-full text-left">
                {promptStarters.map((card) => {
                  const IconComp = card.icon;
                  return (
                    <button
                      key={card.title}
                      type="button"
                      onClick={() => handleSendMessage(card.prompt)}
                      className="p-3.5 rounded-[10px] bg-[#151D26] hover:bg-[#1B2530] border border-white/[0.08] hover:border-white/[0.18] transition-all flex items-start space-x-3 text-left group cursor-pointer shadow-sm"
                    >
                      <div className="w-8 h-8 rounded-md bg-[#1B2530] group-hover:bg-[#20B8E5]/10 group-hover:text-[#20B8E5] text-[#9AA6B2] flex items-center justify-center flex-shrink-0 transition-colors mt-0.5">
                        <IconComp size={15} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <span className="text-xs sm:text-sm font-semibold text-[#F5F7FA] block leading-snug">
                          {card.title}
                        </span>
                        <span className="text-[11px] text-[#6B7785] block mt-0.5 leading-normal line-clamp-2">
                          {card.desc}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Chat Input Box: Visible & properly positioned below 2x2 grid */}
              <div className="w-full max-w-2xl mx-auto pt-1">
                <VideoChatInput
                  onSend={handleSendMessage}
                  disabled={isGenerating}
                  placeholder="Describe your Reel commercial scene..."
                />
              </div>
            </div>
          </div>
        </main>
      ) : (
        /* STATE 2: Active 50/50 Split Screen on Submit */
        <main className="pt-20 pb-2 px-2 sm:px-4 flex-1 flex flex-col lg:flex-row overflow-hidden h-[calc(100vh-5rem)]">
          {/* Left Column (50% Desktop): Chat & Agent Reasoning */}
          <div className="w-full lg:w-1/2 h-full flex flex-col relative bg-[#0E141B] border-r border-white/[0.08] overflow-hidden">
            {/* Scrollable Conversation Stream - Scrolled internally via ref, NEVER scrolling the window */}
            <div
              ref={messagesContainerRef}
              className="flex-1 overflow-y-auto pb-32 pt-4 px-4 sm:px-6"
            >
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`py-4 border-b border-white/[0.04] ${
                    message.role === "assistant" ? "bg-white/[0.01]" : ""
                  }`}
                >
                  <div className="max-w-2xl mx-auto flex items-start space-x-3.5">
                    {message.role === "user" ? (
                      <div className="w-7 h-7 rounded-full bg-[#1B2530] border border-white/[0.1] text-[#F5F7FA] text-xs font-semibold flex items-center justify-center flex-shrink-0 mt-0.5">
                        U
                      </div>
                    ) : (
                      <div className="w-7 h-7 rounded-lg bg-[#20B8E5]/10 border border-[#20B8E5]/20 text-[#20B8E5] flex items-center justify-center flex-shrink-0 mt-0.5">
                        <Sparkles size={14} />
                      </div>
                    )}

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1.5">
                        <span className="text-xs font-semibold text-[#F5F7FA]">
                          {message.role === "user" ? "You" : "Hipoclipse AI"}
                        </span>
                        <span className="text-[11px] text-[#6B7785]">
                          {message.timestamp}
                        </span>
                      </div>

                      {/* Step-by-step progress checklist with pulsing dot & badge */}
                      {message.thoughts && message.thoughts.length > 0 && (
                        <ThoughtContainer
                          thoughts={message.thoughts}
                          isThinking={isGenerating}
                          duration={
                            status === "completed"
                              ? artifact?.generationDuration ?? 11.8
                              : undefined
                          }
                        />
                      )}

                      <div className="text-sm text-[#F5F7FA] leading-relaxed whitespace-pre-wrap">
                        {message.content}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Bottom Input Area in Active Chat */}
            <div className="p-3 border-t border-white/[0.08] bg-[#0E141B] z-20">
              <div className="max-w-2xl mx-auto">
                <VideoChatInput
                  onSend={handleSendMessage}
                  disabled={isGenerating}
                  placeholder="Follow up or refine scene prompt..."
                />
              </div>
            </div>
          </div>

          {/* Right Column (50% Desktop): Video Studio Panel */}
          <div className="w-full lg:w-1/2 h-full flex-shrink-0">
            <VideoStudioPanel
              artifact={artifact}
              status={status}
              displayProgress={displayProgress}
              currentStage={currentStage}
              error={error}
              isOpen={true}
              onClose={() => {}}
              onSelectVariation={selectVariation}
              onUpdatePrompt={updatePrompt}
              onRegenerate={() => {
                if (artifact?.prompt) startGeneration(artifact.prompt);
              }}
              onRetry={retry}
            />
          </div>
        </main>
      )}
    </div>
  );
}

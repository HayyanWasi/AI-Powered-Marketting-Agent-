"use client";

import { Bot, ArrowUpRight } from "lucide-react";
import { ClimbingBoxLoader } from "react-spinners";
import { ChatMessage } from "./types";
import ThoughtContainer from "./ThoughtContainer";

interface Props {
  message: ChatMessage;
  onViewArtifact?: (artifactId: string) => void;
}

export default function AssistantMessageBubble({
  message,
  onViewArtifact,
}: Props) {
  return (
    <div className="py-4 border-b border-white/[0.04] bg-white/[0.01]">
      <div className="max-w-3xl mx-auto px-4 flex items-start space-x-3.5">
        {/* Assistant Avatar */}
        <div className="w-7 h-7 rounded-lg bg-[#20B8E5]/10 border border-[#20B8E5]/20 text-[#20B8E5] flex items-center justify-center flex-shrink-0 mt-0.5">
          <Bot size={14} />
        </div>

        <div className="flex-1 min-w-0">
          {/* Header with Name and Timestamp */}
          <div className="flex items-center space-x-2 mb-1.5">
            <span className="text-xs font-semibold text-[#F5F7FA]">Hipoclipse Agent</span>
            <span className="text-[11px] text-[#6B7785]">{message.timestamp}</span>
          </div>

          {/* Reasoning Process */}
          {message.thoughts && message.thoughts.length > 0 && (
            <ThoughtContainer
              thoughts={message.thoughts}
              isThinking={message.isThinking}
              duration={message.thoughtDuration}
            />
          )}

          {/* Assistant Text Output */}
          {message.content ? (
            <div className="text-sm text-[#F5F7FA] leading-relaxed space-y-2 select-text font-sans">
              {message.content}
            </div>
          ) : message.isStreaming || message.isThinking ? (
            <div className="py-3 flex items-center space-x-3 text-xs text-[#9AA6B2]">
              <ClimbingBoxLoader color="#00c2ee" size={10} />
              <span className="text-[11px] text-[#00c2ee] animate-pulse font-medium">
                Generating content... This may take some time
              </span>
            </div>
          ) : null}

          {/* View Drafts in Studio Trigger */}
          {message.artifactId && onViewArtifact && (
            <div className="mt-3">
              <button
                type="button"
                onClick={() => onViewArtifact(message.artifactId!)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-[#151D26] hover:bg-[#1B2530] border border-white/[0.08] hover:border-white/[0.16] text-xs font-medium text-[#F5F7FA] transition-colors cursor-pointer"
              >
                <span>Open in Campaign Studio</span>
                <ArrowUpRight size={13} className="text-[#20B8E5]" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

"use client";

import { ChatMessage } from "./types";

interface Props {
  message: ChatMessage;
}

export default function UserMessageBubble({ message }: Props) {
  return (
    <div className="py-4 border-b border-white/[0.04]">
      <div className="max-w-3xl mx-auto px-4 flex items-start space-x-3.5">
        {/* User Avatar */}
        <div className="w-7 h-7 rounded-full bg-[#1B2530] border border-white/[0.1] text-[#F5F7FA] text-xs font-semibold flex items-center justify-center flex-shrink-0 mt-0.5">
          U
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2 mb-1">
            <span className="text-xs font-semibold text-[#F5F7FA]">You</span>
            <span className="text-[11px] text-[#6B7785]">{message.timestamp}</span>
          </div>

          <div className="text-sm text-[#F5F7FA] leading-relaxed whitespace-pre-wrap">
            {message.content}
          </div>
        </div>
      </div>
    </div>
  );
}

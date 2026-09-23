"use client";

import { useState, useRef, useEffect } from "react";
import {
  ArrowUp,
  Share2,
  Rocket,
  FileText,
  Workflow,
} from "lucide-react";

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  isInitial?: boolean;
  onSelectPrompt?: (prompt: string) => void;
}

const promptCards = [
  {
    title: "Create a LinkedIn campaign",
    desc: "Generate 3 high-converting post variations with hook frameworks",
    icon: Share2,
    prompt: "Create 3 high-converting LinkedIn post variations targeting enterprise B2B decision-makers.",
  },
  {
    title: "Product launch strategy",
    desc: "Multi-touch announcement plan for enterprise commercial buyers",
    icon: Rocket,
    prompt: "Develop an enterprise product launch campaign highlighting measurable ROI and sales automation.",
  },
  {
    title: "Write high-converting copy",
    desc: "Compelling value propositions focused on verifiable commercial ROI",
    icon: FileText,
    prompt: "Write conversational commercial ad copy that drives B2B replenishment and reduces friction.",
  },
  {
    title: "Multi-channel campaign",
    desc: "Orchestrate WhatsApp, LinkedIn, and mobile commercial channels",
    icon: Workflow,
    prompt: "Build an omnichannel campaign orchestrating WhatsApp agents and LinkedIn post touches.",
  },
];

export default function ChatInput({
  onSend,
  disabled = false,
  placeholder = "Message Hipoclipse AI...",
  isInitial = false,
  onSelectPrompt,
}: Props) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [text]);

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4">
      {/* New Chat / Empty State Welcome Section */}
      {isInitial && (
        <div className="mb-8 text-center space-y-6">
          <div className="space-y-2">
            <h1 className="text-2xl sm:text-3xl font-semibold text-[#F5F7FA] tracking-tight">
              How can I help with your campaign?
            </h1>
            <p className="text-xs sm:text-sm text-[#9AA6B2] max-w-md mx-auto leading-relaxed">
              Describe your campaign goal, audience, or idea and Hipoclipse AI will help you build it.
            </p>
          </div>

          {/* 4 Clean Rectangular Suggested Prompt Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left max-w-2xl mx-auto">
            {promptCards.map((card) => {
              const IconComp = card.icon;
              return (
                <button
                  key={card.title}
                  type="button"
                  onClick={() => {
                    if (onSelectPrompt) onSelectPrompt(card.prompt);
                    else onSend(card.prompt);
                  }}
                  className="p-3.5 rounded-[10px] bg-[#151D26] hover:bg-[#1B2530] border border-white/[0.08] hover:border-white/[0.18] transition-all flex items-start space-x-3 text-left group cursor-pointer shadow-sm"
                >
                  <div className="w-7 h-7 rounded-md bg-[#1B2530] group-hover:bg-[#20B8E5]/10 group-hover:text-[#20B8E5] text-[#9AA6B2] flex items-center justify-center flex-shrink-0 transition-colors mt-0.5">
                    <IconComp size={15} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-xs font-semibold text-[#F5F7FA] block leading-snug">
                      {card.title}
                    </span>
                    <span className="text-[11px] text-[#6B7785] block mt-0.5 leading-normal line-clamp-1">
                      {card.desc}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* ChatGPT-Style Rounded Message Input Box */}
      <div className="relative rounded-[16px] bg-[#151D26] border border-white/[0.08] focus-within:border-[#20B8E5] transition-colors p-3 shadow-sm">
        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={placeholder}
          className="w-full bg-transparent text-sm text-[#F5F7FA] placeholder-[#6B7785] focus:outline-none resize-none pr-12 pl-1 py-1 leading-relaxed max-h-40 font-sans"
        />

        <div className="flex items-center justify-between pt-2 border-t border-white/[0.04] text-[11px] text-[#6B7785] pl-1">
          <span>Shift + Return for new line</span>

          <button
            type="button"
            onClick={handleSubmit}
            disabled={!text.trim() || disabled}
            aria-label="Send message"
            className={`w-7 h-7 rounded-lg flex items-center justify-center transition-all cursor-pointer ${text.trim() && !disabled
              ? "bg-[#20B8E5] text-[#0E141B] hover:bg-[#1BA1CA] shadow-sm"
              : "bg-white/[0.05] text-[#6B7785] cursor-not-allowed"
              }`}
          >
            <ArrowUp size={15} strokeWidth={2.5} />
          </button>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Check, Loader2 } from "lucide-react";
import { ThoughtStep } from "./types";

interface Props {
  thoughts: ThoughtStep[];
  isThinking?: boolean;
  duration?: number;
}

export default function ThoughtContainer({
  thoughts,
  isThinking = false,
  duration,
}: Props) {
  // Active thinking open, finished collapsed by default
  const [isExpanded, setIsExpanded] = useState(isThinking);

  if (!thoughts || thoughts.length === 0) return null;

  return (
    <div className="mb-3 rounded-lg bg-[#151D26]/70 border border-white/[0.08] overflow-hidden text-xs transition-colors">
      {/* Compact Header Bar */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center justify-between text-[#9AA6B2] hover:text-[#F5F7FA] hover:bg-white/[0.02] transition-colors cursor-pointer"
      >
        <div className="flex items-center space-x-2">
          {isThinking ? (
            <div className="flex items-center space-x-1.5 text-[#20B8E5]">
              <Loader2 size={13} className="animate-spin" />
              <span className="font-medium text-[#F5F7FA]">Reasoning...</span>
            </div>
          ) : (
            <div className="flex items-center space-x-1.5 text-[#9AA6B2]">
              <Check size={13} className="text-[#10B981]" />
              <span className="font-medium text-[#F5F7FA]">
                Thought for {duration !== undefined ? `${duration}s` : "a few seconds"}
              </span>
            </div>
          )}
        </div>

        <div className="flex items-center space-x-1 text-[11px] text-[#6B7785]">
          {isExpanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        </div>
      </button>

      {/* Accordion Steps Checklist */}
      {isExpanded && (
        <div className="px-3 pb-2.5 pt-1 border-t border-white/[0.04] space-y-2">
          {thoughts.map((step, idx) => {
            const isLast = idx === thoughts.length - 1;
            const isCurrentActive = isThinking && isLast;

            return (
              <div key={step.id} className="flex items-start space-x-2 text-[11px]">
                <div className="mt-0.5 flex-shrink-0">
                  {isCurrentActive ? (
                    <div className="w-3.5 h-3.5 rounded-full border-2 border-[#20B8E5] border-t-transparent animate-spin" />
                  ) : (
                    <Check size={12} className="text-[#10B981]" />
                  )}
                </div>

                <div className="flex-1 min-w-0 leading-tight">
                  <span className={isCurrentActive ? "text-[#20B8E5]" : "text-[#9AA6B2]"}>
                    {step.title}
                  </span>
                  {step.detail && (
                    <p className="text-[10px] text-[#6B7785] mt-0.5">
                      {step.detail}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

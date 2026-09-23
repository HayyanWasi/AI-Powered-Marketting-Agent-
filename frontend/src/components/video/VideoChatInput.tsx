"use client";

import { useState, useRef, useEffect } from "react";
import { ArrowUp } from "lucide-react";

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function VideoChatInput({
  onSend,
  disabled = false,
  placeholder = "Describe your Reel commercial scene...",
}: Props) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        140
      )}px`;
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
    <div className="w-full">
      {/* ChatGPT-Style 16px Rounded Message Input Box */}
      <div className="relative rounded-[16px] bg-[#151D26] border border-white/[0.08] focus-within:border-[#20B8E5] transition-colors p-3 shadow-sm">
        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={placeholder}
          className="w-full bg-transparent text-sm text-[#F5F7FA] placeholder-[#6B7785] focus:outline-none resize-none pr-12 pl-1 py-1 leading-relaxed max-h-36 font-sans"
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

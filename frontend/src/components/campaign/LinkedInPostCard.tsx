"use client";

import { useState, useEffect, useRef } from "react";
import { Copy, Check, Edit3, CheckCheck, RefreshCw, Share2 } from "lucide-react";
import { LinkedInPost } from "./types";
import { linkedinApi } from "@/lib/api";

interface Props {
  post: LinkedInPost;
  index: number;
}

export default function LinkedInPostCard({ post, index }: Props) {
  const [editedContent, setEditedContent] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [published, setPublished] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const currentContent = editedContent !== null ? editedContent : post.content;

  // Auto-resize textarea when editing
  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [isEditing, currentContent]);

  // Dynamically derived metrics
  const charCount = currentContent.length;
  const wordCount = currentContent.trim() ? currentContent.trim().split(/\s+/).length : 0;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(currentContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleRegenerate = () => {
    setIsRegenerating(true);
    setTimeout(() => {
      setIsRegenerating(false);
    }, 800);
  };

  const handlePublish = async () => {
    if (!currentContent || isPublishing) return;
    setIsPublishing(true);
    try {
      const res = await linkedinApi.publishPost(currentContent);
      if (res && res.status === "success") {
        setPublished(true);
      } else {
        alert("Could not publish to LinkedIn. Please check backend connection.");
      }
    } catch (err: any) {
      alert(err.message || "Failed to publish post to LinkedIn.");
    } finally {
      setIsPublishing(false);
    }
  };

  return (
    <div className="rounded-[10px] bg-[#151D26] border border-white/[0.08] p-5 transition-colors">
      {/* Top Header Tag & Action Buttons */}
      <div className="flex items-center justify-between pb-3.5 mb-4 border-b border-white/[0.06]">
        <span className="text-xs font-semibold text-[#F5F7FA]">
          {post.tag || `Variation ${index + 1}`}
        </span>

        <div className="flex items-center space-x-1.5">
          {/* Regenerate action */}
          <button
            type="button"
            onClick={handleRegenerate}
            title="Regenerate this variation"
            className="p-1.5 rounded-md text-[#9AA6B2] hover:text-[#F5F7FA] hover:bg-white/[0.04] transition-colors cursor-pointer"
          >
            <RefreshCw size={13} className={isRegenerating ? "animate-spin text-[#20B8E5]" : ""} />
          </button>

          {/* Inline Edit Toggle */}
          <button
            type="button"
            onClick={() => {
              if (!isEditing && editedContent === null) {
                setEditedContent(post.content);
              }
              setIsEditing(!isEditing);
            }}
            className="px-2.5 py-1 rounded-md text-xs font-medium text-[#9AA6B2] hover:text-[#F5F7FA] hover:bg-white/[0.04] transition-colors flex items-center space-x-1 cursor-pointer"
          >
            {isEditing ? (
              <>
                <Check size={12} className="text-[#10B981]" />
                <span className="text-[#10B981]">Done</span>
              </>
            ) : (
              <>
                <Edit3 size={12} />
                <span>Edit</span>
              </>
            )}
          </button>

          {/* Primary Copy Button */}
          <button
            type="button"
            onClick={handleCopy}
            className={`px-3 py-1 rounded-md text-xs font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer ${copied
                ? "bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30"
                : "bg-white/[0.06] text-[#F5F7FA] hover:bg-white/[0.1] border border-white/[0.08]"
              }`}
          >
            {copied ? (
              <>
                <CheckCheck size={12} />
                <span>Copied</span>
              </>
            ) : (
              <>
                <Copy size={12} />
                <span>Copy</span>
              </>
            )}
          </button>

          {/* Instant Publish to LinkedIn via Unipile */}
          <button
            type="button"
            disabled={isPublishing || published}
            onClick={handlePublish}
            className={`px-3 py-1 rounded-md text-xs font-semibold flex items-center space-x-1.5 transition-all cursor-pointer ${published
                ? "bg-[#10B981] text-[#0E141B]"
                : isPublishing
                  ? "bg-[#20B8E5]/50 text-[#0E141B] cursor-wait"
                  : "bg-[#20B8E5] hover:bg-[#1BA1CA] text-[#0E141B]"
              }`}
          >
            {published ? (
              <>
                <Check size={12} />
                <span>Published!</span>
              </>
            ) : isPublishing ? (
              <>
                <RefreshCw size={12} className="animate-spin" />
                <span>Posting...</span>
              </>
            ) : (
              <>
                <Share2 size={12} />
                <span>Publish to LinkedIn</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Mock Author Info */}
      <div className="flex items-center space-x-2.5 mb-3.5">
        <div className="w-8 h-8 rounded-full bg-[#1B2530] border border-white/[0.1] text-[#F5F7FA] font-bold text-xs flex items-center justify-center flex-shrink-0">
          H
        </div>
        <div className="flex-1 min-w-0 leading-tight">
          <div className="flex items-center space-x-1.5">
            <span className="text-xs font-semibold text-[#F5F7FA] truncate">
              {post.authorName}
            </span>
            <span className="text-[10px] text-[#6B7785]">• 1st</span>
          </div>
          <p className="text-[11px] text-[#6B7785] truncate">
            {post.authorTitle}
          </p>
        </div>
      </div>

      {/* Post Content Body */}
      <div className="mb-4">
        {isEditing ? (
          <textarea
            ref={textareaRef}
            value={currentContent}
            onChange={(e) => setEditedContent(e.target.value)}
            className="w-full bg-[#0E141B] border border-[#20B8E5]/40 rounded-lg p-3 text-xs sm:text-sm text-[#F5F7FA] focus:outline-none leading-relaxed resize-none font-sans"
          />
        ) : (
          <div className="text-xs sm:text-sm text-[#F5F7FA]/90 whitespace-pre-wrap leading-relaxed font-sans select-text">
            {currentContent || (
              <span className="text-[#6B7785] italic flex items-center space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#20B8E5] animate-pulse" />
                <span>Drafting copy...</span>
              </span>
            )}
          </div>
        )}
      </div>

      {/* Bottom Metrics Bar */}
      <div className="pt-3 border-t border-white/[0.04] flex items-center justify-between text-[11px] text-[#6B7785] font-mono">
        <span>{charCount} chars • {wordCount} words</span>
        <span>{charCount > 3000 ? "Over LinkedIn limit" : "Optimal feed length"}</span>
      </div>
    </div>
  );
}

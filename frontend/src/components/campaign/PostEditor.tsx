"use client";

import { useState, useId } from "react";
import { Loader2, AlertCircle, Check } from "lucide-react";

export interface PostEditorData {
  id: string;
  hook: string;
  body: string;
  cta_text: string;
  full_content?: string;
  status: string;
}

interface Props {
  post: PostEditorData;
  onSave: (fields: { hook: string; body: string; cta_text: string }) => Promise<void>;
  onCancel: () => void;
  isSaving: boolean;
  saveError: string | null;
}

const MAX_CHARACTERS = 3000;

export default function PostEditor({
  post,
  onSave,
  onCancel,
  isSaving,
  saveError,
}: Props) {
  const [hook, setHook] = useState(post.hook || "");
  const [body, setBody] = useState(post.body || post.full_content || "");
  const [ctaText, setCtaText] = useState(post.cta_text || "");

  const hookId = useId();
  const bodyId = useId();
  const ctaId = useId();

  // Canonical composition matching backend: f"{hook}\n\n{body}\n\n{cta}".strip()
  const composedPreview = `${hook}\n\n${body}\n\n${ctaText}`.trim();
  const characterCount = composedPreview.length;
  const isOverLimit = characterCount > MAX_CHARACTERS;

  const isDirty =
    hook !== (post.hook || "") ||
    body !== (post.body || post.full_content || "") ||
    ctaText !== (post.cta_text || "");

  const handleCancel = () => {
    if (isDirty) {
      const confirmDiscard = window.confirm(
        "You have unsaved changes. Are you sure you want to discard them?"
      );
      if (!confirmDiscard) return;
    }
    onCancel();
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isDirty || isSaving || isOverLimit) return;
    await onSave({
      hook,
      body,
      cta_text: ctaText,
    });
  };

  return (
    <form
      onSubmit={handleSave}
      className="rounded-[12px] border border-[#187CA4] bg-white p-5 shadow-sm space-y-4"
    >
      <div className="flex items-center justify-between border-b border-[#DCE6EC] pb-3">
        <h3 className="text-[14px] font-semibold text-[#18222D]">
          Edit Post Content
        </h3>
        <span
          className={`text-[12px] font-medium ${
            isOverLimit
              ? "text-[#D9381E] font-semibold"
              : characterCount > 2700
              ? "text-[#B78103]"
              : "text-[#52606B]"
          }`}
          aria-live="polite"
        >
          {characterCount.toLocaleString()} / {MAX_CHARACTERS.toLocaleString()}{" "}
          characters
        </span>
      </div>

      {saveError && (
        <div
          role="alert"
          className="rounded-[8px] border border-[#F5C2C7] bg-[#FDF2F2] p-3 text-[12.5px] text-[#D9381E] flex items-start gap-2"
        >
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{saveError}</span>
        </div>
      )}

      {isOverLimit && (
        <div
          role="alert"
          className="rounded-[8px] border border-[#F5C2C7] bg-[#FDF2F2] p-2.5 text-[12px] text-[#D9381E] flex items-center gap-2"
        >
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>
            Combined content exceeds the LinkedIn limit of 3,000 characters by{" "}
            {(characterCount - MAX_CHARACTERS).toLocaleString()} characters.
          </span>
        </div>
      )}

      {/* Hook Input */}
      <div className="space-y-1.5">
        <label
          htmlFor={hookId}
          className="block text-[12.5px] font-semibold text-[#18222D]"
        >
          Hook / Headline
        </label>
        <input
          id={hookId}
          type="text"
          value={hook}
          onChange={(e) => setHook(e.target.value)}
          placeholder="Attention-grabbing opening line..."
          disabled={isSaving}
          className="w-full rounded-[8px] border border-[#DCE6EC] bg-[#F8FBFC] px-3 py-2 text-[13.5px] text-[#18222D] placeholder-[#52606B]/60 focus:border-[#187CA4] focus:bg-white focus:outline-none focus:ring-1 focus:ring-[#187CA4] disabled:opacity-60 transition-colors"
        />
      </div>

      {/* Body Input */}
      <div className="space-y-1.5">
        <label
          htmlFor={bodyId}
          className="block text-[12.5px] font-semibold text-[#18222D]"
        >
          Body Copy
        </label>
        <textarea
          id={bodyId}
          rows={6}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Main core content and value points..."
          disabled={isSaving}
          className="w-full rounded-[8px] border border-[#DCE6EC] bg-[#F8FBFC] px-3 py-2.5 text-[13.5px] leading-relaxed text-[#18222D] placeholder-[#52606B]/60 focus:border-[#187CA4] focus:bg-white focus:outline-none focus:ring-1 focus:ring-[#187CA4] disabled:opacity-60 transition-colors resize-y"
        />
      </div>

      {/* CTA Input */}
      <div className="space-y-1.5">
        <label
          htmlFor={ctaId}
          className="block text-[12.5px] font-semibold text-[#18222D]"
        >
          Call to Action (CTA)
        </label>
        <input
          id={ctaId}
          type="text"
          value={ctaText}
          onChange={(e) => setCtaText(e.target.value)}
          placeholder="Link, question, or closing invitation..."
          disabled={isSaving}
          className="w-full rounded-[8px] border border-[#DCE6EC] bg-[#F8FBFC] px-3 py-2 text-[13.5px] text-[#18222D] placeholder-[#52606B]/60 focus:border-[#187CA4] focus:bg-white focus:outline-none focus:ring-1 focus:ring-[#187CA4] disabled:opacity-60 transition-colors"
        />
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-3 pt-2 border-t border-[#DCE6EC]">
        <button
          type="button"
          onClick={handleCancel}
          disabled={isSaving}
          className="rounded-[8px] border border-[#DCE6EC] bg-white px-4 py-2 text-[13px] font-medium text-[#52606B] hover:bg-[#F8FBFC] hover:text-[#18222D] focus:outline-none focus:ring-2 focus:ring-[#187CA4]/20 disabled:opacity-50 transition-colors cursor-pointer"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={!isDirty || isSaving || isOverLimit}
          className="flex items-center gap-1.5 rounded-[8px] bg-[#187CA4] px-4 py-2 text-[13px] font-medium text-white hover:bg-[#146485] focus:outline-none focus:ring-2 focus:ring-[#187CA4]/40 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm cursor-pointer"
        >
          {isSaving ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Saving Changes...</span>
            </>
          ) : (
            <>
              <Check className="w-4 h-4" />
              <span>Save Changes</span>
            </>
          )}
        </button>
      </div>
    </form>
  );
}

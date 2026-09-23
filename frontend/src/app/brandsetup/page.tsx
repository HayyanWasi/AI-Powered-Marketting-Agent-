"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { companyApi, CompanyProfile } from "@/lib/api";
import { getActiveBrandId, setActiveBrandId } from "@/lib/activeBrand";
import { ArrowRight, ArrowLeft, Check, Loader2, X, Plus, Lock } from "lucide-react";

const TOTAL = 3;

// Backend limits — mirrored from CompanyProfileCreate / CompanyProfileUpdate
// (backend/src/models/company.py) so invalid data is stopped before submission.
const MAX_NAME = 255; // company_name max_length
const MAX_VOICE = 1000; // brand_tone max_length
const MAX_GUIDELINES = 5000; // brand_guidelines max_length (serialized JSON)

function str(v: unknown): string {
  return typeof v === "string" ? v : "";
}

/** Parse the stored guidelines JSON into the fields this form edits. */
function parseGuidelines(p: CompanyProfile) {
  let g: Record<string, unknown> = {};
  try {
    const v: unknown = JSON.parse(p.brand_guidelines);
    if (v && typeof v === "object" && !Array.isArray(v)) g = v as Record<string, unknown>;
  } catch {
    /* Non-JSON legacy prose: nothing structured to prefill. */
  }
  return {
    companyName: p.company_name || str(g.companyName),
    targetAudience: str(g.targetAudience),
    coreMission: str(g.description),
    trackRecord: str(g.trackRecord),
    brandVoice: p.brand_tone || str(g.toneMessage),
    guardrails: Array.isArray(g.negativeGuardrails)
      ? (g.negativeGuardrails.filter((x): x is string => typeof x === "string"))
      : [],
  };
}

function BrandSetup() {
  const { user, isLoading, setIsAuthModalOpen } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const forceNew = searchParams.get("mode") === "new";

  const [loading, setLoading] = useState(true); // fetching the active brand
  const [companyId, setCompanyId] = useState<string | null>(null); // set = edit mode
  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);
  // Captured at submit time: whether the save was an edit or a create. `companyId`
  // is set to the new id right after a create, so the success screen must not
  // derive create-vs-update from it (that would mislabel a create as "updated").
  const [savedAsEdit, setSavedAsEdit] = useState(false);
  const [error, setError] = useState("");
  const [invalid, setInvalid] = useState<Record<string, boolean>>({});

  // Fields
  const [companyName, setCompanyName] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [coreMission, setCoreMission] = useState("");
  const [trackRecord, setTrackRecord] = useState("");
  const [brandVoice, setBrandVoice] = useState("");
  const [guardrails, setGuardrails] = useState<string[]>([]);
  const [guardrailDraft, setGuardrailDraft] = useState("");

  const isEdit = companyId !== null;
  const progress = done ? 100 : Math.round((step / TOTAL) * 100);

  const resetFields = useCallback(() => {
    setCompanyName("");
    setTargetAudience("");
    setCoreMission("");
    setTrackRecord("");
    setBrandVoice("");
    setGuardrails([]);
    setGuardrailDraft("");
    setInvalid({});
    setStep(1);
  }, []);

  // Load the active brand (edit) or start empty (create). Never flash an empty
  // form before existing values arrive: `loading` gates the whole screen.
  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (isLoading) return;
      setError("");
      if (!user) {
        // Not signed in yet — offer an empty create form; auth is enforced on submit.
        resetFields();
        setCompanyId(null);
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const active = getActiveBrandId(user.id);
        const list = await companyApi.list();
        if (cancelled) return;
        const canEdit = !forceNew && active && list.some((p) => p.id === active);
        if (canEdit) {
          const profile = await companyApi.get(active as string);
          if (cancelled) return;
          const f = parseGuidelines(profile);
          setCompanyName(f.companyName);
          setTargetAudience(f.targetAudience);
          setCoreMission(f.coreMission);
          setTrackRecord(f.trackRecord);
          setBrandVoice(f.brandVoice);
          setGuardrails(f.guardrails);
          setGuardrailDraft("");
          setInvalid({});
          setStep(1);
          setCompanyId(profile.id);
        } else {
          resetFields();
          setCompanyId(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Could not load your brand. Please retry.");
          setCompanyId(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [user, isLoading, forceNew, resetFields]);

  const flag = (field: string, bad: boolean) =>
    setInvalid((prev) => ({ ...prev, [field]: bad }));

  const validateStep = (s: number): boolean => {
    const next: Record<string, boolean> = {};
    if (s === 1) next.companyName = !companyName.trim() || companyName.trim().length > MAX_NAME;
    if (s === 2) {
      next.coreMission = !coreMission.trim();
      next.trackRecord = !trackRecord.trim();
    }
    if (s === 3) next.brandVoice = !brandVoice.trim() || brandVoice.length > MAX_VOICE;
    setInvalid((prev) => ({ ...prev, ...next }));
    return !Object.values(next).some(Boolean);
  };

  const addGuardrail = () => {
    const v = guardrailDraft.trim();
    if (!v) return;
    if (guardrails.some((g) => g.toLowerCase() === v.toLowerCase())) {
      setGuardrailDraft("");
      return;
    }
    setGuardrails((prev) => [...prev, v]);
    setGuardrailDraft("");
  };

  const removeGuardrail = (i: number) =>
    setGuardrails((prev) => prev.filter((_, idx) => idx !== i));

  const buildGuidelines = (): string =>
    JSON.stringify({
      companyName: companyName.trim(),
      targetAudience: targetAudience.trim(),
      description: coreMission.trim(),
      trackRecord: trackRecord.trim(),
      toneMessage: brandVoice.trim(),
      negativeGuardrails: guardrails,
    });

  const handleNext = () => {
    if (!validateStep(step)) return;
    if (step < TOTAL) {
      setStep((s) => s + 1);
      return;
    }
    void finish();
  };

  const finish = async () => {
    // Validate every step's rules before writing.
    const okAll = [1, 2, 3].every((s) => validateStep(s));
    if (!okAll) {
      setError("Please complete the required fields before saving.");
      return;
    }
    if (!user) {
      setIsAuthModalOpen(true);
      return;
    }

    const guidelines = buildGuidelines();
    if (guidelines.length > MAX_GUIDELINES) {
      setError(
        `Your brand details are too long (${guidelines.length}/${MAX_GUIDELINES} characters). ` +
        "Please shorten your mission, track record, or guardrails.",
      );
      return;
    }

    setSavedAsEdit(companyId !== null);
    setSaving(true);
    setError("");
    try {
      let saved: CompanyProfile;
      if (companyId) {
        // EDIT: send only the keys this form owns. The backend merges
        // brand_guidelines, so advanced fields (industry, website, etc.) that
        // this UI does not show are preserved rather than overwritten.
        saved = await companyApi.update(companyId, {
          company_name: companyName.trim(),
          brand_guidelines: guidelines,
          brand_tone: brandVoice.trim(),
        });
      } else {
        saved = await companyApi.create({
          company_name: companyName.trim(),
          brand_guidelines: guidelines,
          brand_tone: brandVoice.trim(),
        });
      }
      if (!saved?.id) throw new Error("The server did not confirm a saved brand.");
      setCompanyId(saved.id);
      setActiveBrandId(user.id, saved.id);
      setDone(true);
    } catch (e) {
      // Keep the entered values; surface the backend's message when it is useful.
      const msg =
        e instanceof Error && e.message && e.message !== "[object Object]"
          ? e.message
          : "Could not save your brand. Please retry.";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const voiceOver = brandVoice.length > MAX_VOICE;

  return (
    <div className="min-h-screen bg-[#f6f7f8] text-[#1f2a30] flex flex-col">
      {/* Slim header */}
      <header className="h-14 shrink-0 border-b border-[#e6e9ec] bg-white/80 backdrop-blur flex items-center justify-between px-4 sm:px-8">
        <Link
          href="/"
          className="flex items-center gap-2 font-semibold text-[#1f2a30] hover:opacity-85 transition-opacity"
          title="Hipoclipse Landing Page"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.png" alt="Hipoclipse" className="w-7 h-7 rounded-md object-contain" />
          <span>Hipoclipse</span>
        </Link>
        {!done && !loading && (
          <span className="text-[12.5px] text-[#8a949c]">
            {isEdit ? "Editing brand" : "New brand"} · Step {step} of {TOTAL}
          </span>
        )}
      </header>

      {/* Loader / progress bar */}
      <div className="h-1 bg-[#e6e9ec] shrink-0">
        <div
          className="h-full bg-[#1174b8] rounded-r-full transition-[width] duration-500 ease-out"
          style={{ width: `${loading ? 8 : progress}%` }}
        />
      </div>

      <main className="flex-1 flex items-start sm:items-center justify-center px-4 py-10">
        <div className="w-full max-w-xl">
          {loading || isLoading ? (
            <div className="flex flex-col items-center justify-center py-24 text-[#8a949c]">
              <Loader2 size={26} className="animate-spin text-[#1174b8]" />
              <p className="text-[13.5px] mt-3">Loading your brand…</p>
            </div>
          ) : !user ? (
            <div className="rounded-[16px] border border-[#e6e9ec] bg-white p-8 sm:p-10 text-center shadow-sm">
              <div className="w-13 h-13 rounded-full bg-[#eef4f8] text-[#1174b8] grid place-items-center mx-auto mb-4">
                <Lock size={24} />
              </div>
              <h2 className="text-[21px] font-semibold text-[#1f2a30]">Sign in required</h2>
              <p className="text-[13.5px] text-[#7a848c] mt-2 mb-6 max-w-sm mx-auto">
                Please sign in or create an account before configuring your brand profile.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={() => setIsAuthModalOpen(true)}
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-[9px] bg-[#1174b8] hover:bg-[#0e5f99] text-white text-[14px] font-semibold px-6 py-2.5 transition-colors cursor-pointer"
                >
                  Sign In or Register
                </button>
                <button
                  type="button"
                  onClick={() => router.push("/")}
                  className="w-full sm:w-auto rounded-[9px] border border-[#dfe4e7] bg-white text-[#5a6771] hover:text-[#1f2a30] hover:bg-[#f4f6f7] text-[14px] font-medium px-5 py-2.5 transition-colors cursor-pointer"
                >
                  Return Home
                </button>
              </div>
            </div>
          ) : done ? (
            <div className="text-center py-10">
              <div className="w-14 h-14 rounded-full bg-[#e7f4ec] border border-[#c7e6d3] grid place-items-center text-[#1f8a5b] mx-auto mb-5">
                <Check size={26} />
              </div>
              <h1 className="text-[24px] font-semibold text-[#1f2a30]">
                {savedAsEdit ? "Brand updated" : "Your brand is set up"}
              </h1>
              <p className="text-[14px] text-[#7a848c] mt-2 max-w-sm mx-auto">
                {companyName} {savedAsEdit ? "has been updated." : "is ready."} You can build campaigns in
                your brand voice now.
              </p>
              <div className="flex items-center justify-center gap-2.5 mt-7">
                <button
                  type="button"
                  onClick={() => router.push("/new-campaign")}
                  className="inline-flex items-center gap-2 rounded-[9px] bg-[#1174b8] hover:bg-[#0e5f99] text-white text-[14px] font-semibold px-5 py-2.5 transition-colors"
                >
                  Start a campaign <ArrowRight size={16} />
                </button>
                <button
                  type="button"
                  onClick={() => router.push("/dashboard")}
                  className="rounded-[9px] border border-[#dfe4e7] bg-white text-[#5a6771] hover:text-[#1f2a30] hover:bg-[#f4f6f7] text-[14px] font-medium px-5 py-2.5 transition-colors"
                >
                  Go to dashboard
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Step heading */}
              {step === 1 && (
                <StepHead
                  eyebrow="Brand"
                  title={isEdit ? "Edit your brand" : "Let's set up your brand"}
                  sub="Start with the basics so we can personalise everything we create for you."
                />
              )}
              {step === 2 && (
                <StepHead
                  eyebrow="What we do"
                  title="What we do & proven track record"
                  sub="Your core mission and real milestones. The AI uses these to back up claims."
                />
              )}
              {step === 3 && (
                <StepHead
                  eyebrow="Voice"
                  title="Brand tone & voice signature"
                  sub="Natural language communication style instructions enforced during agent interactions."
                />
              )}

              <div className="rounded-[16px] border border-[#e6e9ec] bg-white p-6 sm:p-8 shadow-sm mt-6">
                {step === 1 && (
                  <div className="space-y-5">
                    <FieldWrap
                      label="Company or business name"
                      required
                      invalid={invalid.companyName}
                      error={
                        companyName.trim().length > MAX_NAME
                          ? `Keep the name under ${MAX_NAME} characters.`
                          : "Add your company name to continue."
                      }
                    >
                      <input
                        value={companyName}
                        maxLength={MAX_NAME}
                        onChange={(e) => {
                          setCompanyName(e.target.value);
                          flag("companyName", false);
                        }}
                        placeholder="e.g. Hipoclipse"
                        className={inputCls(invalid.companyName)}
                      />
                    </FieldWrap>
                    <FieldWrap
                      label="Target audience"
                      hint="Who you're trying to reach. Optional, but it sharpens the output."
                    >
                      <input
                        value={targetAudience}
                        onChange={(e) => setTargetAudience(e.target.value)}
                        placeholder="e.g. B2B SaaS founders and marketing leads"
                        className={inputCls(false)}
                      />
                    </FieldWrap>
                  </div>
                )}

                {step === 2 && (
                  <div className="space-y-5">
                    <FieldWrap
                      label="What does your company do? (Core Mission)"
                      required
                      invalid={invalid.coreMission}
                      error="Tell us what your company does."
                    >
                      <textarea
                        rows={3}
                        value={coreMission}
                        onChange={(e) => {
                          setCoreMission(e.target.value);
                          flag("coreMission", false);
                        }}
                        placeholder="Describe your core value proposition, solutions, and services…"
                        className={textareaCls(invalid.coreMission)}
                      />
                    </FieldWrap>
                    <FieldWrap
                      label="What have you done? (Track Record & Key Achievements)"
                      required
                      invalid={invalid.trackRecord}
                      error="Add at least one real achievement."
                    >
                      <textarea
                        rows={3}
                        value={trackRecord}
                        onChange={(e) => {
                          setTrackRecord(e.target.value);
                          flag("trackRecord", false);
                        }}
                        placeholder="e.g. Helped 200+ teams launch on LinkedIn, 3x average reply rate…"
                        className={textareaCls(invalid.trackRecord)}
                      />
                    </FieldWrap>
                  </div>
                )}

                {step === 3 && (
                  <div className="space-y-5">
                    <div>
                      <FieldWrap
                        label="Brand Voice & Communication Style Message"
                        required
                        invalid={invalid.brandVoice}
                        error={
                          voiceOver
                            ? `Brand voice must be under ${MAX_VOICE} characters.`
                            : "Describe how your brand should sound."
                        }
                      >
                        <textarea
                          rows={6}
                          value={brandVoice}
                          onChange={(e) => {
                            setBrandVoice(e.target.value);
                            flag("brandVoice", false);
                          }}
                          placeholder="Tell the AI how your brand communicates. e.g. 'We sound like a supportive, experienced partner: friendly, direct, and pragmatic. We avoid high-pressure sales talk and marketing fluff…'"
                          className={textareaCls(invalid.brandVoice)}
                        />
                      </FieldWrap>
                      <p
                        className={`text-[11.5px] text-right mt-1.5 ${voiceOver ? "text-[#b3392b] font-medium" : "text-[#9aa4ac]"
                          }`}
                      >
                        {brandVoice.length}/{MAX_VOICE} characters
                      </p>
                    </div>

                    {/* Negative guardrails — optional; produces string[] */}
                    <div>
                      <label className="block text-[13px] font-semibold text-[#1f2a30] mb-1.5">
                        What should the AI never say or do?
                      </label>
                      <div className="flex gap-2">
                        <input
                          value={guardrailDraft}
                          onChange={(e) => setGuardrailDraft(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              addGuardrail();
                            }
                          }}
                          placeholder="e.g. Avoid exaggerated claims"
                          className={inputCls(false)}
                        />
                        <button
                          type="button"
                          onClick={addGuardrail}
                          disabled={!guardrailDraft.trim()}
                          className="shrink-0 inline-flex items-center gap-1.5 rounded-[9px] border border-[#dfe4e7] bg-white text-[#1f2a30] hover:bg-[#f4f6f7] disabled:opacity-50 text-[13.5px] font-medium px-3.5 py-2.5 transition-colors"
                        >
                          <Plus size={15} /> Add
                        </button>
                      </div>
                      <p className="text-[12px] text-[#9aa4ac] mt-1.5">
                        Add words, claims, topics, or communication styles the brand should avoid.
                      </p>
                      {guardrails.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-3">
                          {guardrails.map((g, i) => (
                            <span
                              key={`${g}-${i}`}
                              className="inline-flex items-center gap-1.5 rounded-full bg-[#eef4f8] border border-[#d6e6f1] text-[#1f2a30] text-[12.5px] pl-3 pr-1.5 py-1"
                            >
                              {g}
                              <button
                                type="button"
                                onClick={() => removeGuardrail(i)}
                                aria-label={`Remove ${g}`}
                                className="rounded-full p-0.5 text-[#5a6771] hover:text-[#b3392b] hover:bg-white transition-colors"
                              >
                                <X size={13} />
                              </button>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {error && <p className="text-[12.5px] text-[#b3392b] mt-4">{error}</p>}
              </div>

              {/* Footer nav */}
              <div className="flex items-center justify-between mt-5">
                {step > 1 ? (
                  <button
                    type="button"
                    onClick={() => setStep((s) => s - 1)}
                    disabled={saving}
                    className="inline-flex items-center gap-1.5 text-[13.5px] font-medium text-[#5a6771] hover:text-[#1f2a30] rounded-[8px] px-3 py-2 hover:bg-[#eef0f2] transition-colors"
                  >
                    <ArrowLeft size={15} /> Back
                  </button>
                ) : (
                  <span />
                )}

                <button
                  type="button"
                  onClick={handleNext}
                  disabled={saving}
                  className="inline-flex items-center gap-2 rounded-[9px] bg-[#1174b8] hover:bg-[#0e5f99] disabled:opacity-60 text-white text-[14px] font-semibold px-5 py-2.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1174b8]/40"
                >
                  {saving ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />{" "}
                      {isEdit ? "Saving changes…" : "Setting up your brand…"}
                    </>
                  ) : step < TOTAL ? (
                    <>
                      Next <ArrowRight size={16} />
                    </>
                  ) : (
                    <>
                      {isEdit ? "Save changes" : "Complete setup"} <Check size={16} />
                    </>
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}

export default function BrandSetupPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#f6f7f8] grid place-items-center">
          <Loader2 size={26} className="animate-spin text-[#1174b8]" />
        </div>
      }
    >
      <BrandSetup />
    </Suspense>
  );
}

/* ── helpers ──────────────────────────────────────────────────────────── */

function StepHead({ eyebrow, title, sub }: { eyebrow: string; title: string; sub: string }) {
  return (
    <div>
      <p className="text-[11px] font-semibold tracking-[0.14em] uppercase text-[#1174b8] mb-2">
        {eyebrow}
      </p>
      <h1 className="text-[24px] sm:text-[28px] font-semibold text-[#1f2a30] leading-tight">
        {title}
      </h1>
      <p className="text-[14px] text-[#7a848c] mt-2 max-w-lg">{sub}</p>
    </div>
  );
}

function FieldWrap({
  label,
  required,
  hint,
  invalid,
  error,
  children,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  invalid?: boolean;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-[13px] font-semibold text-[#1f2a30] mb-1.5">
        {label} {required && <span className="text-[#1174b8]">*</span>}
      </label>
      {children}
      {invalid && error ? (
        <p className="text-[12px] text-[#b3392b] mt-1.5">{error}</p>
      ) : hint ? (
        <p className="text-[12px] text-[#9aa4ac] mt-1.5">{hint}</p>
      ) : null}
    </div>
  );
}

const inputCls = (bad?: boolean) =>
  `w-full rounded-[9px] border px-3.5 py-2.5 text-[14px] text-[#26333b] placeholder-[#a6afb5] focus:outline-none transition-colors ${bad
    ? "border-[#d98a80] focus:border-[#b3392b] focus:ring-2 focus:ring-[#b3392b]/15"
    : "border-[#dfe4e7] focus:border-[#1174b8] focus:ring-2 focus:ring-[#1174b8]/15"
  }`;

const textareaCls = (bad?: boolean) =>
  `${inputCls(bad)} leading-relaxed resize-y min-h-[92px]`;

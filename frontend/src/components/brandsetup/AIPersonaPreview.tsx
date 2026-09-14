"use client";

import { useState } from "react";
import { BrandProfileData, AIPersonaGuess } from "./types";
import {
  Sparkles,
  Bot,
  ShieldCheck,
  CheckCircle2,
  Database,
  ArrowRight,
} from "lucide-react";

interface Props {
  formData: BrandProfileData;
  personaGuess: AIPersonaGuess;
  isSynthesizing: boolean;
}

export default function AIPersonaPreview({
  formData,
  personaGuess,
  isSynthesizing,
}: Props) {
  const [selectedChannel, setSelectedChannel] = useState<"whatsapp" | "web">("whatsapp");
  const [isSaved, setIsSaved] = useState(false);

  const handleSaveToVector = () => {
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 3000);
  };

  return (
    <div className="space-y-6 sticky top-28">
      {/* Main AI Persona Card */}
      <div className="rounded-2xl bg-[#141B24] border border-[#272F38] p-6 shadow-2xl relative overflow-hidden">
        {/* Glow backdrop */}
        <div className="absolute -top-16 -right-16 w-52 h-52 bg-[#d75dff]/15 rounded-full blur-3xl pointer-events-none" />

        {/* Card Header */}
        <div className="flex items-center justify-between pb-4 mb-5 border-b border-[#272F38]">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#00c2ee] to-[#d75dff] flex items-center justify-center text-white shadow-md">
              <Bot size={18} />
            </div>
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-white/50 block">
                AI Persona Output
              </span>
              <h3 className="text-base font-bold text-white">
                Synthesized Brand Character
              </h3>
            </div>
          </div>

          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 size={12} />
            <span>{personaGuess.confidenceScore}% Match</span>
          </span>
        </div>

        {/* Loading Overlay when synthesizing */}
        {isSynthesizing ? (
          <div className="py-16 flex flex-col items-center justify-center text-center space-y-4">
            <div className="relative w-16 h-16 flex items-center justify-center">
              <div className="absolute inset-0 rounded-full border-2 border-[#d75dff]/20 animate-ping" />
              <div className="w-12 h-12 rounded-full border-2 border-t-[#00c2ee] border-r-[#d75dff] border-b-[#edae3e] border-l-transparent animate-spin" />
              <Sparkles size={20} className="text-white" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-white">Analyzing Company Story...</h4>
              <p className="text-xs text-white/50 max-w-xs mt-1">
                Extracting tone vectors, company achievements, and persona archetype
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Persona Archetype Badge */}
            <div className="p-4 rounded-xl bg-[#0E151C] border border-[#272F38]">
              <span className="text-[11px] uppercase tracking-wider text-[#00c2ee] font-semibold block mb-1">
                Extracted Archetype
              </span>
              <div className="text-xl font-black text-white tracking-tight flex items-center space-x-2">
                <span className="text-gradient">{personaGuess.archetype}</span>
              </div>
              <p className="text-xs text-white/70 mt-2 leading-relaxed italic">
                &ldquo;{personaGuess.personaSummary}&rdquo;
              </p>
            </div>

            {/* Voice Spectrum Bars */}
            <div>
              <span className="text-xs font-semibold text-white/80 block mb-3">
                Voice Signature Spectrum
              </span>
              <div className="space-y-3">
                {personaGuess.tonePillars.map((pillar) => (
                  <div key={pillar.name}>
                    <div className="flex justify-between text-xs mb-1 font-medium">
                      <span className="text-white/70">{pillar.name}</span>
                      <span className="text-white font-bold">{pillar.percentage}%</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-[#0E151C] border border-white/5 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${pillar.color} transition-all duration-500`}
                        style={{ width: `${pillar.percentage}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Live Channel Simulation (WhatsApp / Web) */}
            <div className="pt-2">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold text-white/80">
                  Simulated Agent Tone
                </span>
                <div className="flex items-center space-x-1 p-0.5 rounded-lg bg-[#0E151C] border border-[#272F38]">
                  <button
                    type="button"
                    onClick={() => setSelectedChannel("whatsapp")}
                    className={`px-2.5 py-0.5 rounded-md text-[11px] font-semibold transition-all cursor-pointer ${
                      selectedChannel === "whatsapp"
                        ? "bg-[#25D366]/20 text-[#25D366] border border-[#25D366]/30"
                        : "text-white/40 hover:text-white"
                    }`}
                  >
                    WhatsApp
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedChannel("web")}
                    className={`px-2.5 py-0.5 rounded-md text-[11px] font-semibold transition-all cursor-pointer ${
                      selectedChannel === "web"
                        ? "bg-[#00c2ee]/20 text-[#00c2ee] border border-[#00c2ee]/30"
                        : "text-white/40 hover:text-white"
                    }`}
                  >
                    Web Agent
                  </button>
                </div>
              </div>

              {/* Chat Bubble Mockup */}
              <div
                className={`p-4 rounded-xl border text-xs leading-relaxed relative ${
                  selectedChannel === "whatsapp"
                    ? "bg-[#0E201B] border-[#25D366]/20 text-white"
                    : "bg-[#0E151C] border-[#00c2ee]/20 text-white"
                }`}
              >
                <div className="flex items-center space-x-2 mb-2 pb-1.5 border-b border-white/10">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      selectedChannel === "whatsapp" ? "bg-[#25D366]" : "bg-[#00c2ee]"
                    } animate-pulse`}
                  />
                  <span className="font-bold text-[11px] text-white/90">
                    {formData.companyName || "Hipoclipse"} Autonomous Agent
                  </span>
                  <span className="text-[10px] text-white/40 ml-auto">Live Preview</span>
                </div>
                <p className="text-white/90">
                  {personaGuess.simulatedAgentGreeting}
                </p>
              </div>
            </div>

            {/* Save & Vector Sync Button */}
            <div className="pt-2">
              <button
                type="button"
                onClick={handleSaveToVector}
                className="w-full py-3.5 px-4 rounded-xl bg-gradient-to-r from-[#00c2ee] via-[#d75dff] to-[#edae3e] hover:opacity-95 text-black font-extrabold text-xs uppercase tracking-wider flex items-center justify-center space-x-2 transition-all shadow-xl shadow-black/60 cursor-pointer active:scale-[0.99]"
              >
                <Database size={15} />
                <span>
                  {isSaved ? "Saved to 1,536-dim Vector Store!" : "Save & Sync Brand Memory"}
                </span>
                <ArrowRight size={14} />
              </button>

              <div className="flex items-center justify-center space-x-1.5 text-[11px] text-white/50 mt-2.5">
                <ShieldCheck size={13} className="text-emerald-400" />
                <span>Governed by Enterprise LLM Safety Guardrails</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Quick Summary Pill Card */}
      <div className="rounded-2xl bg-[#141B24] border border-[#272F38] p-5 shadow-xl">
        <span className="text-xs font-semibold text-white/80 block mb-2">
          Specializations Emboldened
        </span>
        <div className="flex flex-wrap gap-1.5">
          {formData.specializations.map((spec) => (
            <span
              key={spec}
              className="px-2 py-0.5 rounded-md bg-white/5 text-[11px] text-white/70"
            >
              ✓ {spec}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

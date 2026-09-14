"use client";

import { useState, useEffect, useCallback } from "react";
import { ShieldAlert, ShieldCheck, RefreshCw, RotateCcw, Loader2 } from "lucide-react";
import { circuitBreakerApi } from "@/lib/api";

interface CBStatus {
  state: string;
  tripped_at?: string | null;
  trip_reason?: string | null;
  cooldown_hours?: number;
  can_proceed?: boolean;
  message?: string;
  error?: string;
}

export default function CircuitBreakerCard() {
  const [status, setStatus] = useState<CBStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);
  const [resetMsg, setResetMsg] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    try {
      const res = await circuitBreakerApi.getStatus();
      setStatus(res);
    } catch (e) {
      console.warn("Could not load circuit breaker:", e);
      setStatus({ state: "unknown", message: "Could not fetch status" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadStatus(); }, [loadStatus]);

  const handleReset = async () => {
    setResetting(true);
    setResetMsg(null);
    try {
      const res = await circuitBreakerApi.reset();
      setResetMsg(res.message);
      await loadStatus();
    } catch (e: unknown) {
      setResetMsg(e instanceof Error ? e.message : "Reset failed");
    } finally {
      setResetting(false);
    }
  };

  const isOpen = status?.state === "open";
  const isHealthy = status?.state === "closed" || status?.can_proceed === true;

  return (
    <div className={`rounded-2xl border overflow-hidden transition-all ${
      isOpen
        ? "bg-rose-950/20 border-rose-500/30"
        : isHealthy
          ? "bg-[#151C25] border-emerald-500/20"
          : "bg-[#151C25] border-zinc-800/60"
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800/60">
        <div className="flex items-center gap-2.5">
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${
            isOpen ? "bg-rose-500/15" : isHealthy ? "bg-emerald-500/15" : "bg-zinc-700/40"
          }`}>
            {isOpen
              ? <ShieldAlert size={14} className="text-rose-400" />
              : <ShieldCheck size={14} className="text-emerald-400" />
            }
          </div>
          <div>
            <p className="text-sm font-semibold text-zinc-100">Circuit Breaker</p>
            <p className="text-[10px] text-zinc-500">Automation safety switch</p>
          </div>
        </div>
        <button
          onClick={loadStatus}
          className="w-7 h-7 rounded-lg bg-zinc-800 hover:bg-zinc-700 flex items-center justify-center text-zinc-400 transition-all"
        >
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Body */}
      <div className="px-5 py-4 space-y-4">
        {loading ? (
          <div className="flex items-center gap-2 text-zinc-600 text-xs">
            <Loader2 size={13} className="animate-spin" />
            Checking status…
          </div>
        ) : (
          <>
            {/* State Badge */}
            <div className="flex items-center justify-between">
              <span className="text-xs text-zinc-400 font-medium">Current State</span>
              <span className={`px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wide border ${
                isOpen
                  ? "text-rose-400 bg-rose-400/10 border-rose-400/20"
                  : isHealthy
                    ? "text-emerald-400 bg-emerald-400/10 border-emerald-400/20"
                    : "text-zinc-400 bg-zinc-700/40 border-zinc-600/40"
              }`}>
                {status?.state ?? "unknown"}
              </span>
            </div>

            {/* Message */}
            <p className="text-xs leading-relaxed text-zinc-400">
              {status?.message ?? "Unable to determine circuit breaker state."}
            </p>

            {/* Details when open */}
            {isOpen && (
              <div className="space-y-1.5 text-[11px] text-zinc-500 pl-3 border-l-2 border-rose-500/30">
                {status?.trip_reason && (
                  <p><span className="text-zinc-400">Reason:</span> {status.trip_reason}</p>
                )}
                {status?.tripped_at && (
                  <p><span className="text-zinc-400">Tripped at:</span> {new Date(status.tripped_at).toLocaleString("en-PK")}</p>
                )}
                {status?.cooldown_hours && (
                  <p><span className="text-zinc-400">Cooldown:</span> {status.cooldown_hours}h</p>
                )}
              </div>
            )}

            {/* Reset success msg */}
            {resetMsg && (
              <div className={`text-[11px] px-3 py-2 rounded-lg border ${
                resetMsg.includes("reset") || resetMsg.includes("CLOSED")
                  ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                  : "text-rose-400 bg-rose-500/10 border-rose-500/20"
              }`}>
                {resetMsg}
              </div>
            )}

            {/* Reset Button */}
            <button
              onClick={handleReset}
              disabled={resetting || (!isOpen && isHealthy)}
              className={`w-full h-9 rounded-xl text-xs font-medium transition-all flex items-center justify-center gap-2 ${
                isOpen
                  ? "bg-rose-600 hover:bg-rose-500 text-white"
                  : "bg-zinc-800 text-zinc-500 cursor-not-allowed opacity-50"
              }`}
              title={!isOpen ? "Circuit breaker is already closed — no reset needed" : ""}
            >
              {resetting ? <Loader2 size={13} className="animate-spin" /> : <RotateCcw size={13} />}
              {resetting ? "Resetting…" : isOpen ? "Reset Circuit Breaker" : "Automation Running Normally"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

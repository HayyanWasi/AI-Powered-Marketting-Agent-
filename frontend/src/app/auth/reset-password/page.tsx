"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { sanitizeNext } from "@/context/AuthContext";
import { Lock, Loader2, CheckCircle, AlertCircle } from "lucide-react";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const rawNext = searchParams.get("next");
  const safeNext = sanitizeNext(rawNext, "/dashboard");

  const [authorized, setAuthorized] = useState<boolean | null>(null);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    async function checkRecoveryAuthorization() {
      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();

        let hasRecoveryInUrl = false;
        if (typeof window !== "undefined") {
          const params = new URLSearchParams(window.location.search);
          if (params.get("type") === "recovery") hasRecoveryInUrl = true;
          if (window.location.hash.includes("type=recovery")) hasRecoveryInUrl = true;
          if (hasRecoveryInUrl) {
            sessionStorage.setItem("recovery_in_progress", "true");
          }
        }

        const hasMarker =
          (typeof window !== "undefined" &&
            sessionStorage.getItem("recovery_in_progress") === "true") ||
          hasRecoveryInUrl;

        if (!session || !hasMarker) {
          if (typeof window !== "undefined") {
            sessionStorage.removeItem("recovery_in_progress");
          }
          setAuthorized(false);
        } else {
          setAuthorized(true);
        }
      } catch {
        if (typeof window !== "undefined") {
          sessionStorage.removeItem("recovery_in_progress");
        }
        setAuthorized(false);
      }
    }

    void checkRecoveryAuthorization();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match. Please re-enter.");
      return;
    }

    setLoading(true);
    try {
      const { error: updateError } = await supabase.auth.updateUser({ password });

      if (updateError) {
        // Retain recovery_in_progress so user can correct input and retry
        setError(updateError.message || "Failed to update password. Please retry.");
      } else {
        // Success: clear marker and redirect to sanitized next
        if (typeof window !== "undefined") {
          sessionStorage.removeItem("recovery_in_progress");
        }
        setSuccess(true);
        setTimeout(() => {
          router.push(safeNext);
        }, 1200);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  const handleAbandon = () => {
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("recovery_in_progress");
    }
    router.push("/");
  };

  if (authorized === null) {
    return (
      <div className="flex flex-col items-center justify-center p-8 space-y-3 text-center">
        <Loader2 size={36} className="text-[#00c2ee] animate-spin" />
        <p className="text-sm text-[#9AA6B2]">Verifying password recovery session...</p>
      </div>
    );
  }

  if (authorized === false) {
    return (
      <div className="space-y-4 text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#ef4444]/10 border border-[#ef4444]/20 text-[#ef4444] mb-1">
          <AlertCircle size={22} />
        </div>
        <h2 className="text-xl font-semibold text-white">Reset Link Invalid or Expired</h2>
        <p className="text-xs text-[#9AA6B2] leading-relaxed max-w-sm mx-auto">
          This password reset session is invalid, expired, or was already used. Please request a new password reset email.
        </p>
        <div className="pt-2">
          <button
            type="button"
            onClick={handleAbandon}
            className="w-full py-2.5 px-4 rounded-xl bg-[#252C35] hover:bg-[#323B47] text-white text-xs font-semibold transition-colors"
          >
            Return to Sign In
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#00c2ee]/10 border border-[#00c2ee]/20 text-[#00c2ee] mb-2">
          <Lock size={20} />
        </div>
        <h2 className="text-xl font-semibold text-white">Set New Password</h2>
        <p className="text-xs text-[#9AA6B2] mt-1">
          Choose a secure password for your account to complete recovery.
        </p>
      </div>

      {error && (
        <div className="flex items-start gap-2 p-3 rounded-xl bg-[#ef4444]/10 border border-[#ef4444]/20 text-[#ef4444] text-xs">
          <AlertCircle size={15} className="shrink-0 mt-0.5" />
          <span className="leading-snug">{error}</span>
        </div>
      )}

      {success && (
        <div className="flex items-start gap-2 p-3 rounded-xl bg-[#10b981]/10 border border-[#10b981]/20 text-[#10b981] text-xs">
          <CheckCircle size={15} className="shrink-0 mt-0.5" />
          <span className="leading-snug">Password updated successfully! Redirecting you...</span>
        </div>
      )}

      {!success && (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-[#C5D1DE] mb-1.5">
              New Password
            </label>
            <div className="relative">
              <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#6C7A89]" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                required
                minLength={8}
                disabled={loading}
                className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-[#1D2530] border border-[#2F3A48] text-sm text-white placeholder-[#6C7A89] focus:outline-none focus:border-[#00c2ee] focus:ring-1 focus:ring-[#00c2ee] transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-[#C5D1DE] mb-1.5">
              Confirm New Password
            </label>
            <div className="relative">
              <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#6C7A89]" />
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter password"
                required
                minLength={8}
                disabled={loading}
                className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-[#1D2530] border border-[#2F3A48] text-sm text-white placeholder-[#6C7A89] focus:outline-none focus:border-[#00c2ee] focus:ring-1 focus:ring-[#00c2ee] transition-colors"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-[#00c2ee] to-[#d75dff] text-black font-semibold text-xs shadow-md transition-all disabled:opacity-50 flex items-center justify-center gap-2 mt-2 cursor-pointer"
          >
            {loading && <Loader2 size={15} className="animate-spin" />}
            <span>Update Password</span>
          </button>

          <div className="text-center pt-1">
            <button
              type="button"
              onClick={handleAbandon}
              className="text-xs text-[#9AA6B2] hover:text-white transition-colors cursor-pointer"
            >
              Cancel and return to home
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen bg-[#0E151C] text-white flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md p-8 rounded-2xl bg-[#141B24] border border-[#272F38] shadow-2xl">
        <Suspense
          fallback={
            <div className="flex flex-col items-center justify-center p-8 space-y-3 text-center">
              <Loader2 size={36} className="text-[#00c2ee] animate-spin" />
              <p className="text-sm text-[#9AA6B2]">Loading...</p>
            </div>
          }
        >
          <ResetPasswordForm />
        </Suspense>
      </div>
    </div>
  );
}

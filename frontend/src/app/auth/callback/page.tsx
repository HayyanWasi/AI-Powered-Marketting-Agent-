"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { sanitizeNext } from "@/context/AuthContext";
import { Loader2, CheckCircle, AlertCircle } from "lucide-react";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [status, setStatus] = useState<"processing" | "success" | "error">("processing");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let hasRedirected = false;

    // 1. Extract next destination and recovery evidence from URL
    let nextParam: string | null = null;
    let isRecoveryFromUrl = false;

    if (typeof window !== "undefined") {
      const searchParams = new URLSearchParams(window.location.search);
      nextParam = searchParams.get("next");
      if (
        searchParams.get("type") === "recovery" ||
        window.location.search.includes("recovery") ||
        window.location.hash.includes("recovery") ||
        window.location.href.includes("recovery")
      ) {
        isRecoveryFromUrl = true;
      }
    }

    const safeNext = sanitizeNext(nextParam, "/dashboard");

    function executeRedirect(isRecovery: boolean) {
      if (hasRedirected) return;
      hasRedirected = true;

      if (isRecovery) {
        if (typeof window !== "undefined") {
          sessionStorage.setItem("recovery_in_progress", "true");
        }
        setStatus("success");
        router.push(`/auth/reset-password?next=${encodeURIComponent(safeNext)}`);
      } else {
        if (typeof window !== "undefined") {
          sessionStorage.removeItem("recovery_in_progress");
        }
        setStatus("success");
        setTimeout(() => {
          router.push(safeNext);
        }, 1000);
      }
    }

    async function handleAuthCallback() {
      try {
        // 2. Subscribe to auth state changes (catches PASSWORD_RECOVERY event and token exchange)
        const {
          data: { subscription },
        } = supabase.auth.onAuthStateChange((event, session) => {
          if (event === "PASSWORD_RECOVERY" || (session && isRecoveryFromUrl)) {
            subscription.unsubscribe();
            executeRedirect(true);
          } else if (session) {
            subscription.unsubscribe();
            executeRedirect(false);
          } else if (event === "SIGNED_OUT") {
            setStatus("error");
            setErrorMessage("Authentication was cancelled or failed.");
            subscription.unsubscribe();
          }
        });

        // 3. Check for existing / established session
        const { data, error } = await supabase.auth.getSession();

        if (error) {
          subscription.unsubscribe();
          setStatus("error");
          setErrorMessage(error.message);
          return;
        }

        if (data.session) {
          if (isRecoveryFromUrl) {
            subscription.unsubscribe();
            executeRedirect(true);
            return;
          }
          // Delay briefly to allow onAuthStateChange's PASSWORD_RECOVERY event to fire
          // before concluding this is a normal sign-in session
          const graceTimeout = setTimeout(() => {
            if (!hasRedirected) {
              subscription.unsubscribe();
              executeRedirect(false);
            }
          }, 300);
          return () => clearTimeout(graceTimeout);
        }

        // 4. Timeout fallback — only fall through if recovery is NOT detected
        const timeout = setTimeout(() => {
          subscription.unsubscribe();
          if (isRecoveryFromUrl) {
            executeRedirect(true);
          } else {
            executeRedirect(false);
          }
        }, 4000);

        return () => {
          clearTimeout(timeout);
          subscription.unsubscribe();
        };
      } catch (err: unknown) {
        setStatus("error");
        setErrorMessage(err instanceof Error ? err.message : "Authentication failed");
      }
    }

    void handleAuthCallback();
  }, [router]);

  return (
    <div className="min-h-screen bg-[#0E151C] text-white flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md p-8 rounded-2xl bg-[#141B24] border border-[#272F38] shadow-2xl text-center space-y-4">
        {status === "processing" && (
          <>
            <Loader2 size={40} className="text-[#00c2ee] animate-spin mx-auto" />
            <h2 className="text-xl font-semibold">Completing Authentication</h2>
            <p className="text-xs text-[#9AA6B2]">
              Verifying your credentials and establishing a secure session...
            </p>
          </>
        )}

        {status === "success" && (
          <>
            <CheckCircle size={40} className="text-[#10b981] mx-auto animate-bounce" />
            <h2 className="text-xl font-semibold">Authentication Successful</h2>
            <p className="text-xs text-[#9AA6B2]">Redirecting you securely...</p>
          </>
        )}

        {status === "error" && (
          <>
            <AlertCircle size={40} className="text-[#ef4444] mx-auto" />
            <h2 className="text-xl font-semibold">Authentication Error</h2>
            <p className="text-xs text-[#ef4444] bg-[#ef4444]/10 p-2.5 rounded-lg border border-[#ef4444]/20">
              {errorMessage || "Unable to complete authentication. Please try again."}
            </p>
            <button
              type="button"
              onClick={() => router.push("/")}
              className="mt-4 px-4 py-2 rounded-lg bg-[#252C35] hover:bg-[#323B47] text-xs font-medium text-white transition-colors"
            >
              Return Home
            </button>
          </>
        )}
      </div>
    </div>
  );
}

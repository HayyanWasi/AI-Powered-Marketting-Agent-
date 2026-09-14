"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { Loader2, CheckCircle, AlertCircle } from "lucide-react";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [status, setStatus] = useState<"processing" | "success" | "error">("processing");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    async function handleAuthCallback() {
      try {
        // Exchange auth code or hash if present
        const { data, error } = await supabase.auth.getSession();

        if (error) {
          setStatus("error");
          setErrorMessage(error.message);
          return;
        }

        if (data.session) {
          setStatus("success");
          setTimeout(() => {
            router.push("/dashboard");
          }, 1200);
        } else {
          // If hash fragment is being processed by supabase client
          const {
            data: { subscription },
          } = supabase.auth.onAuthStateChange((event, session) => {
            if (session) {
              setStatus("success");
              subscription.unsubscribe();
              setTimeout(() => {
                router.push("/dashboard");
              }, 1200);
            } else if (event === "SIGNED_OUT") {
              setStatus("error");
              setErrorMessage("Authentication was cancelled or failed.");
              subscription.unsubscribe();
            }
          });

          // Timeout fallback
          const timeout = setTimeout(() => {
            subscription.unsubscribe();
            router.push("/dashboard");
          }, 4000);

          return () => clearTimeout(timeout);
        }
      } catch (err: unknown) {
        setStatus("error");
        setErrorMessage(err instanceof Error ? err.message : "Authentication failed");
      }
    }

    handleAuthCallback();
  }, [router]);

  return (
    <div className="min-h-screen bg-[#0E151C] text-white flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md p-8 rounded-2xl bg-[#141B24] border border-[#272F38] shadow-2xl text-center space-y-4">
        {status === "processing" && (
          <>
            <Loader2 size={40} className="text-[#00c2ee] animate-spin mx-auto" />
            <h2 className="text-xl font-semibold">Completing Authentication</h2>
            <p className="text-xs text-[#9AA6B2]">
              Verifying your OAuth 2.0 identity and establishing a secure session...
            </p>
          </>
        )}

        {status === "success" && (
          <>
            <CheckCircle size={40} className="text-[#10b981] mx-auto animate-bounce" />
            <h2 className="text-xl font-semibold">Authentication Successful</h2>
            <p className="text-xs text-[#9AA6B2]">Redirecting you to the dashboard...</p>
          </>
        )}

        {status === "error" && (
          <>
            <AlertCircle size={40} className="text-[#ef4444] mx-auto" />
            <h2 className="text-xl font-semibold">Authentication Error</h2>
            <p className="text-xs text-[#ef4444] bg-[#ef4444]/10 p-2.5 rounded-lg border border-[#ef4444]/20">
              {errorMessage || "Unable to complete OAuth login. Please try again."}
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

"use client";

import React, { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { X, Lock, Mail, AlertCircle, CheckCircle, Loader2 } from "lucide-react";

type AuthMode = "signin" | "signup" | "forgot";

export default function AuthModal() {
  const {
    isAuthModalOpen,
    setIsAuthModalOpen,
    signInWithOAuth,
    signInWithPassword,
    signUp,
    resetPassword,
  } = useAuth();

  const [mode, setMode] = useState<AuthMode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState<"google" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  if (!isAuthModalOpen) return null;

  const validate = (): boolean => {
    setError(null);
    setSuccess(null);

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email || !emailRegex.test(email.trim())) {
      setError("Please enter a valid email address.");
      return false;
    }
    if (mode !== "forgot" && (!password || password.length < 8)) {
      setError("Password must be at least 8 characters long.");
      return false;
    }
    return true;
  };

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      if (mode === "signin") {
        const { error: authErr } = await signInWithPassword(email.trim(), password);
        if (authErr) {
          const errCode = (authErr as { code?: string }).code || "";
          const errMsg = (authErr.message || "").toLowerCase();
          if (errCode === "email_not_confirmed" || errMsg.includes("email not confirmed")) {
            setError("Please confirm your email before signing in.");
          } else if (
            errCode === "invalid_credentials" ||
            errMsg.includes("invalid login credentials")
          ) {
            setError("Invalid login credentials.");
          } else {
            setError(authErr.message || "Failed to sign in. Please verify your credentials.");
          }
        } else {
          setIsAuthModalOpen(false);
        }
      } else if (mode === "signup") {
        const { error: authErr, isExistingUser, message } = await signUp(email.trim(), password);
        if (authErr) {
          setError(authErr.message || "Failed to create account.");
        } else if (isExistingUser) {
          // Existing-email / masked signup: do NOT show "Account created"
          setError(message || "An account with this email already exists. Sign in or reset your password.");
        } else {
          // Genuinely new signup: inform user to check email without auto-signin
          setSuccess(message || "Check your email to confirm your account before signing in.");
        }
      } else if (mode === "forgot") {
        const currentPath =
          typeof window !== "undefined" ? window.location.pathname : "/dashboard";
        const { error: resetErr } = await resetPassword(email.trim(), currentPath);
        if (resetErr) {
          setError(resetErr.message || "Failed to send password reset email.");
        } else {
          setSuccess("Password reset email sent. Please check your inbox.");
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Authentication error occurred.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = async () => {
    setError(null);
    setOauthLoading("google");
    try {
      const { error: authErr } = await signInWithOAuth("google");
      if (authErr) {
        setError(authErr.message || "Failed to start Google sign-in.");
        setOauthLoading(null);
      }
      // On success the browser redirects to Google automatically.
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Google sign-in error.");
      setOauthLoading(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#0d1a20]/45 backdrop-blur-sm">
      {/* Click-outside backdrop */}
      <div
        className="absolute inset-0"
        onClick={() => {
          if (!loading && !oauthLoading) setIsAuthModalOpen(false);
        }}
      />

      {/* Modal */}
      <div className="relative w-full max-w-md bg-white border border-[#e6e9ec] rounded-2xl shadow-xl p-6 sm:p-8 z-10 text-[#1f2a30]">
        {/* Close */}
        <button
          type="button"
          onClick={() => setIsAuthModalOpen(false)}
          aria-label="Close"
          className="absolute top-4 right-4 text-[#9aa4ac] hover:text-[#1f2a30] transition-colors p-1.5 rounded-lg hover:bg-[#f2f4f6] cursor-pointer"
        >
          <X size={18} />
        </button>

        {/* Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-11 h-11 rounded-xl bg-[#e9f2fa] border border-[#cfe4f2] text-[#1174b8] mb-3">
            <Lock size={18} />
          </div>
          <h2 className="text-[19px] font-semibold tracking-tight text-[#1f2a30]">
            {mode === "signin"
              ? "Welcome back"
              : mode === "signup"
              ? "Create your account"
              : "Reset password"}
          </h2>
          <p className="text-[13px] text-[#8a949c] mt-1">
            {mode === "signin"
              ? "Sign in to manage your marketing campaigns"
              : mode === "signup"
              ? "Get started with your AI marketing agent"
              : "Enter your email to receive a password reset link"}
          </p>
        </div>

        {/* Mode tabs */}
        <div className="grid grid-cols-2 p-1 bg-[#f2f4f6] rounded-[10px] border border-[#e6e9ec] mb-5 text-[13px] font-medium">
          <button
            type="button"
            onClick={() => {
              setMode("signin");
              setError(null);
              setSuccess(null);
            }}
            className={`py-2 rounded-[7px] transition-all cursor-pointer ${
              mode === "signin"
                ? "bg-white text-[#1f2a30] shadow-sm font-semibold"
                : "text-[#7a848c] hover:text-[#1f2a30]"
            }`}
          >
            Sign in
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("signup");
              setError(null);
              setSuccess(null);
            }}
            className={`py-2 rounded-[7px] transition-all cursor-pointer ${
              mode === "signup"
                ? "bg-white text-[#1f2a30] shadow-sm font-semibold"
                : "text-[#7a848c] hover:text-[#1f2a30]"
            }`}
          >
            Register
          </button>
        </div>

        {/* Alerts */}
        {error && (
          <div className="flex items-start gap-2 p-3 rounded-[10px] bg-[#fbecea] border border-[#f2cfca] text-[#b3392b] text-[12.5px] mb-4">
            <AlertCircle size={15} className="shrink-0 mt-0.5" />
            <span className="leading-snug">{error}</span>
          </div>
        )}
        {success && (
          <div className="flex items-start gap-2 p-3 rounded-[10px] bg-[#e7f4ec] border border-[#c7e6d3] text-[#1f7a52] text-[12.5px] mb-4">
            <CheckCircle size={15} className="shrink-0 mt-0.5" />
            <span className="leading-snug">{success}</span>
          </div>
        )}

        {/* Google OAuth (only for signin/signup) */}
        {mode !== "forgot" && (
          <>
            <button
              type="button"
              onClick={handleGoogle}
              disabled={loading || oauthLoading !== null}
              className="w-full flex items-center justify-center gap-2.5 py-2.5 px-4 rounded-[10px] bg-white hover:bg-[#f6f8f9] border border-[#dfe4e7] text-[13px] font-medium text-[#1f2a30] transition-colors disabled:opacity-50 cursor-pointer"
            >
              {oauthLoading === "google" ? (
                <Loader2 size={16} className="animate-spin text-[#1174b8]" />
              ) : (
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path
                    fill="#EA4335"
                    d="M12 5c1.6 0 3 .6 4.1 1.7l3.1-3.1C17.3 1.8 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z"
                  />
                  <path
                    fill="#4285F4"
                    d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.6h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.9z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.3s.2-1.6.4-2.3L1.9 7.3C.7 9.7 0 12 0 14.5s.7 4.8 1.9 7.2l3.7-2.9z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23.5c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2-6.4-4.8L1.9 17C3.7 20.8 7.5 23.5 12 23.5z"
                  />
                </svg>
              )}
              <span>Continue with Google</span>
            </button>

            {/* Divider */}
            <div className="relative flex items-center justify-center my-4">
              <div className="border-t border-[#e6e9ec] w-full" />
              <span className="bg-white px-3 text-[10.5px] uppercase tracking-wider text-[#9aa4ac] font-semibold">
                Or with email
              </span>
            </div>
          </>
        )}

        {/* Email form */}
        <form onSubmit={handleEmailAuth} className="space-y-3.5">
          <div>
            <label className="block text-[12px] font-medium text-[#5a6771] mb-1.5">
              Email address
            </label>
            <div className="relative">
              <Mail size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#a6afb5]" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                required
                className="w-full pl-9 pr-3 py-2.5 rounded-[10px] bg-white border border-[#dfe4e7] text-[13.5px] text-[#26333b] placeholder-[#a6afb5] focus:outline-none focus:border-[#1174b8] focus:ring-2 focus:ring-[#1174b8]/15 transition-colors"
              />
            </div>
          </div>

          {mode !== "forgot" && (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-[12px] font-medium text-[#5a6771]">Password</label>
                {mode === "signin" && (
                  <button
                    type="button"
                    onClick={() => {
                      setMode("forgot");
                      setError(null);
                      setSuccess(null);
                    }}
                    className="text-[12px] text-[#1174b8] hover:underline cursor-pointer"
                  >
                    Forgot password?
                  </button>
                )}
              </div>
              <div className="relative">
                <Lock
                  size={15}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-[#a6afb5]"
                />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  required
                  minLength={8}
                  className="w-full pl-9 pr-3 py-2.5 rounded-[10px] bg-white border border-[#dfe4e7] text-[13.5px] text-[#26333b] placeholder-[#a6afb5] focus:outline-none focus:border-[#1174b8] focus:ring-2 focus:ring-[#1174b8]/15 transition-colors"
                />
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={loading || oauthLoading !== null}
            className="w-full py-2.5 px-4 rounded-[10px] bg-[#1174b8] hover:bg-[#0e5f99] text-white font-semibold text-[13.5px] shadow-sm transition-colors disabled:opacity-50 flex items-center justify-center gap-2 mt-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1174b8]/40 cursor-pointer"
          >
            {loading && <Loader2 size={15} className="animate-spin" />}
            <span>
              {mode === "signin"
                ? "Sign in"
                : mode === "signup"
                ? "Create account"
                : "Send reset link"}
            </span>
          </button>

          {mode === "forgot" && (
            <div className="text-center pt-1">
              <button
                type="button"
                onClick={() => {
                  setMode("signin");
                  setError(null);
                  setSuccess(null);
                }}
                className="text-[12.5px] text-[#1174b8] hover:underline font-medium cursor-pointer"
              >
                Back to sign in
              </button>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}

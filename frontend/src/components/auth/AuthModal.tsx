"use client";

import React, { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { X, Lock, Mail, AlertCircle, CheckCircle, Loader2 } from "lucide-react";

export default function AuthModal() {
  const { isAuthModalOpen, setIsAuthModalOpen, signInWithOAuth, signInWithPassword, signUp } =
    useAuth();

  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState<"google" | "github" | null>(null);
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

    if (!password || password.length < 8) {
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
          setError(authErr.message || "Failed to sign in. Please verify credentials.");
        } else {
          setIsAuthModalOpen(false);
        }
      } else {
        const { error: authErr } = await signUp(email.trim(), password);
        if (authErr) {
          setError(authErr.message || "Failed to create account.");
        } else {
          setSuccess("Account created successfully! If required, check your email for confirmation.");
          setTimeout(() => {
            setIsAuthModalOpen(false);
          }, 2500);
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Authentication error occurred.");
    } finally {
      setLoading(false);
    }
  };

  const handleOAuth = async (provider: "google" | "github") => {
    setError(null);
    setOauthLoading(provider);
    try {
      const { error: authErr } = await signInWithOAuth(provider);
      if (authErr) {
        setError(authErr.message || `Failed to initialize ${provider} OAuth.`);
        setOauthLoading(null);
      }
      // Note: If successful, browser will redirect to OAuth provider URL automatically
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : `OAuth ${provider} error.`);
      setOauthLoading(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      {/* Click outside backdrop */}
      <div
        className="absolute inset-0"
        onClick={() => {
          if (!loading && !oauthLoading) setIsAuthModalOpen(false);
        }}
      />

      {/* Modal Container */}
      <div className="relative w-full max-w-md bg-[#121820] border border-[#273240] rounded-2xl shadow-2xl p-6 sm:p-8 z-10 text-white overflow-hidden">
        {/* Glow Accents */}
        <div className="absolute -top-20 -left-20 w-40 h-40 bg-[#00c2ee]/20 blur-3xl rounded-full pointer-events-none" />
        <div className="absolute -bottom-20 -right-20 w-40 h-40 bg-[#d75dff]/20 blur-3xl rounded-full pointer-events-none" />

        {/* Close Button */}
        <button
          type="button"
          onClick={() => setIsAuthModalOpen(false)}
          className="absolute top-5 right-5 text-[#9AA6B2] hover:text-white transition-colors p-1 rounded-lg hover:bg-[#1E2732]"
        >
          <X size={18} />
        </button>

        {/* Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-[#00c2ee]/20 to-[#d75dff]/20 border border-[#00c2ee]/30 text-[#00c2ee] mb-3">
            <Lock size={18} />
          </div>
          <h2 className="text-xl font-bold tracking-tight">
            {mode === "signin" ? "Welcome Back" : "Create an Account"}
          </h2>
          <p className="text-xs text-[#9AA6B2] mt-1">
            {mode === "signin"
              ? "Sign in to manage your AI marketing campaigns"
              : "Get started with autonomous marketing agents"}
          </p>
        </div>

        {/* Mode Selector Tabs */}
        <div className="grid grid-cols-2 p-1 bg-[#0A0E13] rounded-lg border border-[#273240] mb-5 text-xs font-medium">
          <button
            type="button"
            onClick={() => {
              setMode("signin");
              setError(null);
              setSuccess(null);
            }}
            className={`py-2 rounded-md transition-all ${
              mode === "signin"
                ? "bg-[#1E2732] text-white shadow-sm font-semibold"
                : "text-[#9AA6B2] hover:text-white"
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("signup");
              setError(null);
              setSuccess(null);
            }}
            className={`py-2 rounded-md transition-all ${
              mode === "signup"
                ? "bg-[#1E2732] text-white shadow-sm font-semibold"
                : "text-[#9AA6B2] hover:text-white"
            }`}
          >
            Register
          </button>
        </div>

        {/* Feedback Alerts */}
        {error && (
          <div className="flex items-start space-x-2 p-3 rounded-lg bg-[#ef4444]/10 border border-[#ef4444]/25 text-[#ef4444] text-xs mb-4">
            <AlertCircle size={15} className="flex-shrink-0 mt-0.5" />
            <span className="leading-tight">{error}</span>
          </div>
        )}

        {success && (
          <div className="flex items-start space-x-2 p-3 rounded-lg bg-[#10b981]/10 border border-[#10b981]/25 text-[#10b981] text-xs mb-4">
            <CheckCircle size={15} className="flex-shrink-0 mt-0.5" />
            <span className="leading-tight">{success}</span>
          </div>
        )}

        {/* OAuth 2.0 Buttons */}
        <div className="space-y-2.5 mb-5">
          {/* Google OAuth */}
          <button
            type="button"
            onClick={() => handleOAuth("google")}
            disabled={loading || oauthLoading !== null}
            className="w-full flex items-center justify-center space-x-2.5 py-2.5 px-4 rounded-xl bg-[#18212C] hover:bg-[#202C3A] border border-[#2A3747] text-xs font-medium text-[#F3F4F6] transition-all cursor-pointer disabled:opacity-50"
          >
            {oauthLoading === "google" ? (
              <Loader2 size={16} className="animate-spin text-[#00c2ee]" />
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

          {/* GitHub OAuth */}
          <button
            type="button"
            onClick={() => handleOAuth("github")}
            disabled={loading || oauthLoading !== null}
            className="w-full flex items-center justify-center space-x-2.5 py-2.5 px-4 rounded-xl bg-[#18212C] hover:bg-[#202C3A] border border-[#2A3747] text-xs font-medium text-[#F3F4F6] transition-all cursor-pointer disabled:opacity-50"
          >
            {oauthLoading === "github" ? (
              <Loader2 size={16} className="animate-spin text-[#00c2ee]" />
            ) : (
              <svg className="w-4 h-4 fill-current text-white" viewBox="0 0 24 24">
                <path
                  fillRule="evenodd"
                  clipRule="evenodd"
                  d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                />
              </svg>
            )}
            <span>Continue with GitHub</span>
          </button>
        </div>

        {/* Divider */}
        <div className="relative flex items-center justify-center my-4">
          <div className="border-t border-[#273240] w-full" />
          <span className="bg-[#121820] px-3 text-[10px] uppercase tracking-wider text-[#6B7785] font-semibold">
            Or with email
          </span>
        </div>

        {/* Email Form */}
        <form onSubmit={handleEmailAuth} className="space-y-3.5">
          <div>
            <label className="block text-[11px] font-medium text-[#9AA6B2] mb-1">
              Email Address
            </label>
            <div className="relative">
              <Mail
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[#6B7785]"
              />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@enterprise.com"
                required
                className="w-full pl-9 pr-3 py-2 rounded-xl bg-[#0A0E13] border border-[#273240] text-xs text-white placeholder-[#6B7785] focus:outline-none focus:border-[#00c2ee] transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-[#9AA6B2] mb-1">
              Password
            </label>
            <div className="relative">
              <Lock
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[#6B7785]"
              />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                required
                minLength={8}
                className="w-full pl-9 pr-3 py-2 rounded-xl bg-[#0A0E13] border border-[#273240] text-xs text-white placeholder-[#6B7785] focus:outline-none focus:border-[#00c2ee] transition-colors"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || oauthLoading !== null}
            className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-[#00c2ee] to-[#d75dff] text-black font-bold text-xs shadow-lg hover:opacity-95 transition-opacity cursor-pointer disabled:opacity-50 flex items-center justify-center space-x-2 mt-2"
          >
            {loading && <Loader2 size={15} className="animate-spin text-black" />}
            <span>{mode === "signin" ? "Sign In to Workspace" : "Create Workspace Account"}</span>
          </button>
        </form>
      </div>
    </div>
  );
}

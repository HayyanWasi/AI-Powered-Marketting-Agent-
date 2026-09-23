"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { User, Session, AuthError } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabaseClient";

export interface SignUpResult {
  error: AuthError | null;
  data?: {
    user: User | null;
    session: Session | null;
  } | null;
  isExistingUser: boolean;
  message?: string;
}

export function sanitizeNext(param?: string | null, fallback = "/dashboard"): string {
  if (!param) return fallback;
  try {
    const decoded = decodeURIComponent(param).trim();
    if (decoded.startsWith("/") && !decoded.startsWith("//") && !decoded.includes(":")) {
      return decoded;
    }
  } catch {
    // Decoding error fallback
  }
  return fallback;
}

interface AuthContextType {
  user: User | null;
  session: Session | null;
  token: string | null;
  isLoading: boolean;
  isAuthModalOpen: boolean;
  setIsAuthModalOpen: (open: boolean) => void;
  signInWithOAuth: (provider: "google" | "github") => Promise<{ error: AuthError | null }>;
  signInWithPassword: (email: string, password: string) => Promise<{ error: AuthError | null }>;
  signUp: (email: string, password: string) => Promise<SignUpResult>;
  resetPassword: (email: string, next?: string) => Promise<{ error: AuthError | null }>;
  updatePassword: (password: string) => Promise<{ error: AuthError | null }>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Keep an in-memory token accessible synchronously by api.ts
let currentAccessToken: string | null = null;

export function getActiveAccessToken(): string | null {
  return currentAccessToken;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  useEffect(() => {
    // 1. Fetch initial active session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      const accessToken = session?.access_token ?? null;
      setToken(accessToken);
      currentAccessToken = accessToken;
      setIsLoading(false);
    });

    // 2. Subscribe to auth state changes (OAuth redirect, login, logout, token refresh)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      const accessToken = session?.access_token ?? null;
      setToken(accessToken);
      currentAccessToken = accessToken;
      setIsLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const signInWithOAuth = useCallback(
    async (provider: "google" | "github") => {
      const redirectUrl =
        typeof window !== "undefined"
          ? `${window.location.origin}/auth/callback`
          : "http://localhost:3000/auth/callback";

      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: redirectUrl,
        },
      });

      return { error };
    },
    []
  );

  const signInWithPassword = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    return { error };
  }, []);

  const signUp = useCallback(async (email: string, password: string): Promise<SignUpResult> => {
    const redirectUrl =
      typeof window !== "undefined"
        ? `${window.location.origin}/auth/callback`
        : "http://localhost:3000/auth/callback";

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: redirectUrl,
      },
    });

    if (error) {
      return { data: null, error, isExistingUser: false, message: error.message };
    }

    // Masked response detection: Supabase returns identities: [] when user already exists
    const isExisting = Boolean(
      data.user && (!data.user.identities || data.user.identities.length === 0)
    );

    if (isExisting) {
      return {
        data,
        error: null,
        isExistingUser: true,
        message: "An account with this email already exists. Sign in or reset your password.",
      };
    }

    const message = !data.session
      ? "Check your email to confirm your account before signing in."
      : undefined;

    return {
      data,
      error: null,
      isExistingUser: false,
      message,
    };
  }, []);

  const resetPassword = useCallback(
    async (email: string, next?: string): Promise<{ error: AuthError | null }> => {
      const origin =
        typeof window !== "undefined"
          ? window.location.origin
          : "http://localhost:3000";
      const safeNext = sanitizeNext(next, "/dashboard");
      const redirectUrl = `${origin}/auth/reset-password?type=recovery&next=${encodeURIComponent(safeNext)}`;

      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: redirectUrl,
      });
      return { error };
    },
    []
  );

  const updatePassword = useCallback(async (password: string) => {
    return await supabase.auth.updateUser({ password });
  }, []);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    setSession(null);
    setUser(null);
    setToken(null);
    currentAccessToken = null;
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        token,
        isLoading,
        isAuthModalOpen,
        setIsAuthModalOpen,
        signInWithOAuth,
        signInWithPassword,
        signUp,
        resetPassword,
        updatePassword,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

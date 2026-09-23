"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Link2,
  Loader2,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Plug,
} from "lucide-react";
import { linkedinApi, type LinkedInConnectedAccount, ApiError } from "@/lib/api";

type Banner =
  | { kind: "connected"; text: string }
  | { kind: "failed"; text: string }
  | null;

/**
 * In-app LinkedIn connection panel (Unipile Hosted Auth).
 *
 * "Connect LinkedIn" asks the backend for a Hosted Auth URL and performs a full
 * top-level redirect (never an iframe). After Unipile redirects the user back to
 * the hosting page with `?linkedin=connected|failed`, this panel reads that flag,
 * shows the outcome, and refreshes the verified account list.
 */
export default function LinkedInConnections() {
  const [accounts, setAccounts] = useState<LinkedInConnectedAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [banner, setBanner] = useState<Banner>(null);

  const loadAccounts = useCallback(
    async (verify = false): Promise<LinkedInConnectedAccount[] | null> => {
      setLoading(true);
      setError(null);
      try {
        const rows = (await linkedinApi.listConnections(verify)) ?? [];
        setAccounts(rows);
        return rows;
      } catch (err) {
        setError(
          err instanceof ApiError
            ? err.message
            : "Could not load your LinkedIn connections."
        );
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // On return from Hosted Auth, the ?linkedin=connected redirect param is NOT
  // proof of a connection — it only means the browser was sent back. The
  // account is "connected" only if the backend persisted a verified account
  // (via Unipile's notify callback). So we always confirm against the API and
  // derive the banner from that result, never from the URL alone.
  useEffect(() => {
    let outcome: string | null = null;
    if (typeof window !== "undefined") {
      outcome = new URLSearchParams(window.location.search).get("linkedin");
      if (outcome) {
        // Clear the redirect param so a refresh cannot re-trigger this.
        window.history.replaceState({}, "", window.location.pathname);
      }
    }

    void (async () => {
      // Verify live against Unipile when returning from a "success" redirect.
      const rows = await loadAccounts(outcome === "connected");

      if (outcome === "connected") {
        const verified = (rows ?? []).some((a) => a.status === "connected");
        setBanner(
          verified
            ? { kind: "connected", text: "LinkedIn connected and verified." }
            : {
              kind: "failed",
              text: "LinkedIn connection could not be verified. Please reconnect.",
            }
        );
      } else if (outcome === "failed") {
        setBanner({
          kind: "failed",
          text: "LinkedIn connection failed or was cancelled. Please try again.",
        });
      }
    })();
  }, [loadAccounts]);

  const handleConnect = async () => {
    setConnecting(true);
    setError(null);
    try {
      const { url } = await linkedinApi.createConnectionLink();
      // Full top-level redirect to Unipile Hosted Auth (no iframe).
      window.location.href = url;
    } catch (err) {
      setConnecting(false);
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not start LinkedIn connection. Please try again."
      );
    }
  };

  const hasConnected = accounts.some((a) => a.status === "connected");

  return (
    <div className="w-full rounded-2xl bg-[#141B24] border border-[#272F38] p-6 space-y-5">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-[#00c2ee]/10">
          <Link2 size={22} className="text-[#00c2ee]" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-white">LinkedIn Connection</h2>
          <p className="text-xs text-[#9AA6B2]">
            Connect a LinkedIn account securely through Unipile Hosted Auth.
          </p>
        </div>
      </div>

      {banner && (
        <div
          className={`flex items-start gap-2 rounded-lg p-3 text-xs border ${banner.kind === "connected"
              ? "bg-[#10b981]/10 border-[#10b981]/20 text-[#10b981]"
              : "bg-[#ef4444]/10 border-[#ef4444]/20 text-[#ef4444]"
            }`}
        >
          {banner.kind === "connected" ? (
            <CheckCircle size={16} className="mt-0.5 shrink-0" />
          ) : (
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
          )}
          <span>{banner.text}</span>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-2 rounded-lg p-3 text-xs border bg-[#ef4444]/10 border-[#ef4444]/20 text-[#ef4444]">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Connected accounts / states */}
      <div className="space-y-2">
        {loading ? (
          <div className="flex items-center gap-2 text-xs text-[#9AA6B2] py-4">
            <Loader2 size={16} className="animate-spin" />
            Loading your connections…
          </div>
        ) : accounts.length === 0 ? (
          <div className="rounded-lg border border-dashed border-[#272F38] p-4 text-center text-xs text-[#9AA6B2]">
            No LinkedIn account connected yet.
          </div>
        ) : (
          accounts.map((acc) => (
            <div
              key={acc.id}
              className="flex items-center justify-between rounded-lg bg-[#0E151C] border border-[#272F38] px-4 py-3"
            >
              <div className="flex items-center gap-3">
                <Link2 size={18} className="text-[#00c2ee]" />
                <div className="text-xs">
                  <p className="text-white font-medium">
                    {acc.provider} account
                  </p>
                  <p className="text-[#6B7683] font-mono">
                    {acc.unipile_account_id}
                  </p>
                </div>
              </div>
              {acc.status === "connected" ? (
                <span className="flex items-center gap-1 text-[11px] font-medium text-[#10b981] bg-[#10b981]/10 px-2.5 py-1 rounded-full">
                  <CheckCircle size={12} /> Connected
                </span>
              ) : (
                <span className="flex items-center gap-1 text-[11px] font-medium text-[#f59e0b] bg-[#f59e0b]/10 px-2.5 py-1 rounded-full">
                  <AlertCircle size={12} /> Reconnect required
                </span>
              )}
            </div>
          ))
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 pt-1">
        <button
          type="button"
          onClick={handleConnect}
          disabled={connecting}
          className="flex items-center gap-2 rounded-lg bg-[#00c2ee] hover:bg-[#00a9d0] disabled:opacity-60 text-[#0E151C] text-sm font-semibold px-4 py-2 transition-colors"
        >
          {connecting ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Plug size={16} />
          )}
          {hasConnected ? "Connect another account" : "Connect LinkedIn"}
        </button>
        <button
          type="button"
          onClick={() => loadAccounts(true)}
          disabled={loading}
          className="flex items-center gap-2 rounded-lg bg-[#252C35] hover:bg-[#323B47] disabled:opacity-60 text-white text-sm font-medium px-4 py-2 transition-colors"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          Refresh status
        </button>
      </div>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Loader2,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Link2,
} from "lucide-react";
import {
  linkedinApi,
  companyApi,
  type LinkedInConnectedAccount,
  type CompanyProfile,
  ApiError,
} from "@/lib/api";

type Banner = { kind: "connected" | "failed"; text: string } | null;

interface LinkedInConnectPanelProps {
  activeBrand?: CompanyProfile | null;
  connectedAccount?: LinkedInConnectedAccount | null;
  onAccountBound?: (updatedBrand: CompanyProfile) => void;
}

/**
 * Light-themed LinkedIn connection panel (Unipile Hosted Auth), rendered as the
 * "LinkedIn" tab on the Prospects page.
 *
 * Scoped to active brand: displays whether the brand has a bound connected account
 * and allows binding existing or newly authenticated accounts directly to the brand.
 */
export default function LinkedInConnectPanel({
  activeBrand,
  connectedAccount,
  onAccountBound,
}: LinkedInConnectPanelProps) {
  const [accounts, setAccounts] = useState<LinkedInConnectedAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [bindingId, setBindingId] = useState<string | null>(null);
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
          err instanceof ApiError ? err.message : "Could not load your LinkedIn connections."
        );
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    let outcome: string | null = null;
    if (typeof window !== "undefined") {
      outcome = new URLSearchParams(window.location.search).get("linkedin");
      if (outcome) window.history.replaceState({}, "", window.location.pathname);
    }
    void (async () => {
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
        if (verified && activeBrand && !activeBrand.default_linkedin_account_id) {
          const firstConn = (rows ?? []).find((a) => a.status === "connected");
          if (firstConn) {
            try {
              const updated = await companyApi.setLinkedInAccount(activeBrand.id, firstConn.id);
              if (onAccountBound) onAccountBound(updated);
            } catch {
              // ignore
            }
          }
        }
      } else if (outcome === "failed") {
        setBanner({
          kind: "failed",
          text: "LinkedIn connection failed or was cancelled. Please try again.",
        });
      }
    })();
  }, [loadAccounts, activeBrand, onAccountBound]);

  const handleConnect = async () => {
    setConnecting(true);
    setError(null);
    try {
      const { url } = await linkedinApi.createConnectionLink();
      window.location.href = url; // full top-level redirect to Unipile Hosted Auth
    } catch (err) {
      setConnecting(false);
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not start LinkedIn connection. Please try again."
      );
    }
  };

  const handleSetDefault = async (accountId: string) => {
    if (!activeBrand) return;
    setBindingId(accountId);
    setError(null);
    try {
      const updated = await companyApi.setLinkedInAccount(activeBrand.id, accountId);
      if (onAccountBound) onAccountBound(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to set default account for brand");
    } finally {
      setBindingId(null);
    }
  };

  const isBrandBound = !!connectedAccount && connectedAccount.status === "connected";

  return (
    <div className="max-w-xl">
      <div className="rounded-[14px] border border-[#e6e9ec] bg-white p-5 sm:p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <span className="w-10 h-10 rounded-lg bg-[#e9f2fa] text-[#1174b8] grid place-items-center shrink-0">
            <Link2 size={20} />
          </span>
          <div>
            <h2 className="text-[16px] font-semibold text-[#1f2a30]">LinkedIn connection</h2>
            <p className="text-[13px] text-[#8a949c] mt-0.5">
              Connect a LinkedIn account securely through Unipile. You&apos;ll sign in on
              Unipile&apos;s hosted page, then return here.
            </p>
          </div>
        </div>

        {activeBrand && (
          <div className="mt-4 rounded-[10px] border border-[#e6e9ec] bg-[#f8fafc] p-3 text-[13px] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-[#64748b]">Active Brand:</span>
              <strong className="text-[#1e293b]">{activeBrand.company_name}</strong>
            </div>
            {isBrandBound ? (
              <span className="flex items-center gap-1 text-[11px] font-semibold text-[#1f8a5b] bg-[#e7f4ec] px-2.5 py-1 rounded-full">
                <CheckCircle2 size={12} /> Connected
              </span>
            ) : (
              <span className="flex items-center gap-1 text-[11px] font-semibold text-[#9a6212] bg-[#fdf3e3] px-2.5 py-1 rounded-full">
                <AlertCircle size={12} /> Disconnected
              </span>
            )}
          </div>
        )}

        {banner && (
          <div
            className={`flex items-start gap-2 rounded-[10px] p-3 text-[12.5px] border mt-4 ${
              banner.kind === "connected"
                ? "bg-[#e7f4ec] border-[#c7e6d3] text-[#1f7a52]"
                : "bg-[#fbecea] border-[#f2cfca] text-[#b3392b]"
            }`}
          >
            {banner.kind === "connected" ? (
              <CheckCircle2 size={16} className="mt-0.5 shrink-0" />
            ) : (
              <AlertCircle size={16} className="mt-0.5 shrink-0" />
            )}
            <span>{banner.text}</span>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 rounded-[10px] p-3 text-[12.5px] border bg-[#fbecea] border-[#f2cfca] text-[#b3392b] mt-4">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Accounts / states */}
        <div className="mt-4 space-y-2">
          {loading ? (
            <div className="flex items-center gap-2 text-[13px] text-[#8a949c] py-4">
              <Loader2 size={15} className="animate-spin" /> Loading your connections…
            </div>
          ) : accounts.length === 0 ? (
            <div className="rounded-[10px] border border-dashed border-[#d7dde1] p-4 text-center text-[13px] text-[#8a949c]">
              No LinkedIn account connected yet.
            </div>
          ) : (
            accounts.map((acc) => {
              const isDefaultForBrand = Boolean(
                (connectedAccount && connectedAccount.id === acc.id) ||
                (activeBrand?.default_linkedin_account_id && activeBrand.default_linkedin_account_id === acc.id)
              );
              const isConnected = acc.status === "connected";
              return (
                <div
                  key={acc.id}
                  className="flex items-center justify-between rounded-[10px] border border-[#e6e9ec] bg-[#fbfcfc] px-4 py-3"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Link2 size={17} className="text-[#1174b8] shrink-0" />
                    <div className="min-w-0">
                      <p className="text-[13px] font-medium text-[#1f2a30]">
                        {acc.account_name || `${acc.provider} account`}
                      </p>
                      <p className="text-[11.5px] text-[#9aa4ac] font-mono truncate">
                        {acc.unipile_account_id}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {isDefaultForBrand && isConnected ? (
                      <span className="flex items-center gap-1 text-[11px] font-semibold text-[#1f8a5b] bg-[#e7f4ec] px-2.5 py-1 rounded-full shrink-0">
                        <CheckCircle2 size={12} /> Connected / Active Brand
                      </span>
                    ) : isConnected ? (
                      <div className="flex items-center gap-2">
                        <span className="flex items-center gap-1 text-[11px] font-semibold text-[#2563eb] bg-[#eff6ff] px-2 py-0.5 rounded-full shrink-0">
                          Connected
                        </span>
                        {activeBrand && (
                          <button
                            type="button"
                            onClick={() => handleSetDefault(acc.id)}
                            disabled={bindingId === acc.id}
                            className="rounded-[6px] border border-[#2f6fd6] text-[#2f6fd6] hover:bg-[#2f6fd6] hover:text-white px-2 py-0.5 text-[11px] font-semibold transition-colors disabled:opacity-50"
                          >
                            {bindingId === acc.id ? (
                              <Loader2 size={10} className="animate-spin inline" />
                            ) : (
                              `Use for ${activeBrand.company_name}`
                            )}
                          </button>
                        )}
                      </div>
                    ) : (
                      <span className="flex items-center gap-1 text-[11px] font-semibold text-[#9a6212] bg-[#fdf3e3] px-2.5 py-1 rounded-full shrink-0">
                        <AlertCircle size={12} /> Reconnect
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-wrap items-center gap-2.5 mt-5">
          <button
            type="button"
            onClick={handleConnect}
            disabled={connecting}
            className="inline-flex items-center gap-2 rounded-[9px] bg-[#1174b8] hover:bg-[#0e5f99] disabled:opacity-60 text-white text-[13.5px] font-semibold px-4 py-2.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1174b8]/40"
          >
            {connecting ? <Loader2 size={15} className="animate-spin" /> : <Link2 size={15} />}
            {isBrandBound ? "Connect another account" : "Connect LinkedIn"}
          </button>
          <button
            type="button"
            onClick={() => loadAccounts(true)}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-[9px] border border-[#dfe4e7] bg-white text-[#5a6771] hover:text-[#1f2a30] hover:bg-[#f4f6f7] disabled:opacity-60 text-[13.5px] font-medium px-4 py-2.5 transition-colors"
          >
            <RefreshCw size={15} className={loading ? "animate-spin" : ""} /> Refresh status
          </button>
        </div>
      </div>
    </div>
  );
}

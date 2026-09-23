"use client";

import { useState } from "react";
import { Link2, Loader2, AlertCircle, Check, ExternalLink } from "lucide-react";
import { companyApi, CompanyProfile, LinkedInConnectedAccount } from "@/lib/api";

interface Props {
  brand: CompanyProfile;
  connections: LinkedInConnectedAccount[];
  onBrandUpdated: (brand: CompanyProfile) => void;
}

/** Safe, honest label for an account — no fabricated profile name/avatar. */
function accountLabel(a: LinkedInConnectedAccount): string {
  const tail = a.unipile_account_id.slice(-6);
  return `${a.provider || "LinkedIn"} account ·••${tail}`;
}

export default function BrandAccountPanel({ brand, connections, onBrandUpdated }: Props) {
  const [choosing, setChoosing] = useState(false);
  const [selected, setSelected] = useState<string>(brand.default_linkedin_account_id || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [linking, setLinking] = useState(false);

  const current = connections.find((c) => c.id === brand.default_linkedin_account_id) || null;
  const connected = connections.filter((c) => c.status === "connected");
  const hasAny = connections.length > 0;

  const save = async (accountId: string | null) => {
    setSaving(true);
    setError(null);
    try {
      const updated = await companyApi.setLinkedInAccount(brand.id, accountId);
      onBrandUpdated(updated);
      setChoosing(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not update the brand's LinkedIn account.");
    } finally {
      setSaving(false);
    }
  };

  const startConnect = async () => {
    setLinking(true);
    setError(null);
    try {
      const { linkedinApi } = await import("@/lib/api");
      const { url } = await linkedinApi.createConnectionLink();
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not start LinkedIn connection.");
    } finally {
      setLinking(false);
    }
  };

  // ── No accounts connected at all ──
  if (!hasAny) {
    return (
      <div className="rounded-[12px] border border-[#FFE082] bg-[#FFFBEB] p-4 flex items-start justify-between gap-4">
        <div className="flex items-start gap-2.5">
          <Link2 className="w-4 h-4 text-[#B78103] mt-0.5 shrink-0" />
          <div>
            <p className="text-[13px] font-semibold text-[#18222D]">
              Connect a LinkedIn account before scheduling
            </p>
            <p className="text-[12px] text-[#52606B] mt-0.5">
              This brand needs a connected LinkedIn account to publish posts.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={startConnect}
          disabled={linking}
          className="inline-flex items-center gap-1.5 rounded-[8px] bg-[#187CA4] px-3 py-1.5 text-[12.5px] font-semibold text-white hover:bg-[#136384] disabled:opacity-50 shrink-0"
        >
          {linking ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ExternalLink className="w-3.5 h-3.5" />}
          Connect
        </button>
      </div>
    );
  }

  const showSelector = choosing || !current;

  return (
    <div className="rounded-[12px] border border-[#DCE6EC] bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <Link2 className="w-4 h-4 text-[#187CA4] shrink-0" />
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-[#52606B]">
              Brand publishing account
            </p>
            {current ? (
              <p className="text-[13px] text-[#18222D] truncate">
                {accountLabel(current)}
                <span
                  className={`ml-2 text-[10.5px] font-medium uppercase tracking-wider px-1.5 py-0.5 rounded-full border ${
                    current.status === "connected"
                      ? "bg-[#EBFBEE] text-[#2B8A3E] border-[#C3FAC7]"
                      : "bg-[#FDF2F2] text-[#D9381E] border-[#F5C2C7]"
                  }`}
                >
                  {current.status}
                </span>
              </p>
            ) : (
              <p className="text-[13px] text-[#52606B]">No account chosen for this brand yet.</p>
            )}
          </div>
        </div>

        {!showSelector && (
          <button
            type="button"
            onClick={() => {
              setSelected(brand.default_linkedin_account_id || "");
              setChoosing(true);
            }}
            className="text-[12px] font-medium text-[#187CA4] hover:text-[#146485] border border-[#DCE6EC] rounded-[6px] px-2.5 py-1 hover:bg-[#EDF6F9] shrink-0"
          >
            Change account
          </button>
        )}
      </div>

      {error && (
        <div
          role="alert"
          className="mt-3 rounded-[8px] border border-[#F5C2C7] bg-[#FDF2F2] p-2.5 text-[12px] text-[#D9381E] flex items-start gap-2"
        >
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {showSelector && (
        <div className="mt-3 space-y-2.5 border-t border-[#DCE6EC] pt-3">
          <label htmlFor="brand-acct" className="block text-[12px] font-semibold text-[#18222D]">
            Choose one of your connected LinkedIn accounts
          </label>
          <select
            id="brand-acct"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            disabled={saving}
            className="w-full rounded-[8px] border border-[#DCE6EC] bg-[#F8FBFC] px-3 py-2 text-[13px] text-[#18222D] focus:border-[#187CA4] focus:bg-white focus:outline-none focus:ring-1 focus:ring-[#187CA4] disabled:opacity-60"
          >
            <option value="">Select an account…</option>
            {connections.map((c) => (
              <option key={c.id} value={c.id} disabled={c.status !== "connected"}>
                {accountLabel(c)}
                {c.status !== "connected" ? ` (${c.status})` : ""}
              </option>
            ))}
          </select>

          <div className="flex items-center justify-between gap-2 pt-0.5">
            <button
              type="button"
              onClick={startConnect}
              disabled={linking}
              className="inline-flex items-center gap-1 text-[12px] text-[#52606B] hover:text-[#18222D] disabled:opacity-50"
            >
              {linking ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ExternalLink className="w-3.5 h-3.5" />}
              Connect another
            </button>

            <div className="flex items-center gap-2">
              {current && (
                <button
                  type="button"
                  onClick={() => save(null)}
                  disabled={saving}
                  className="text-[12.5px] font-medium text-[#52606B] hover:text-[#D9381E] border border-[#DCE6EC] rounded-[8px] px-3 py-1.5 hover:bg-[#F8FBFC] disabled:opacity-50"
                >
                  Clear
                </button>
              )}
              {choosing && current && (
                <button
                  type="button"
                  onClick={() => {
                    setChoosing(false);
                    setError(null);
                  }}
                  disabled={saving}
                  className="text-[12.5px] font-medium text-[#52606B] hover:text-[#18222D] px-2 py-1.5 disabled:opacity-50"
                >
                  Cancel
                </button>
              )}
              <button
                type="button"
                onClick={() => selected && save(selected)}
                disabled={saving || !selected || connected.length === 0}
                className="inline-flex items-center gap-1.5 rounded-[8px] bg-[#187CA4] px-3.5 py-1.5 text-[12.5px] font-semibold text-white hover:bg-[#136384] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                Save account
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

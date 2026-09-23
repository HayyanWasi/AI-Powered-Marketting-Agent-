"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, AlertTriangle, Loader2, Rocket, Plug } from "lucide-react";
import {
  linkedinApi,
  ApiError,
  type LinkedInConnectedAccount,
} from "@/lib/api";

interface Props {
  /** Real backend campaign id to launch. */
  campaignId?: string;
  /** Number of generated posts; launch is disabled when there are none. */
  postCount: number;
}

/**
 * Launch control for the campaign studio.
 *
 * Shows the signed-in user's verified, connected LinkedIn accounts, requires the
 * user to pick one (auto-selected when only one exists), and calls the real
 * launch endpoint — never a fake success. Arbitrary account ids cannot be
 * entered; only accounts the backend has verified for this user are selectable.
 * The launch endpoint independently re-verifies ownership and connection, so an
 * invalid choice is rejected server-side.
 */
export default function LinkedInLaunchControl({ campaignId, postCount }: Props) {
  const [accounts, setAccounts] = useState<LinkedInConnectedAccount[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [launched, setLaunched] = useState(false);

  const loadAccounts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = (await linkedinApi.listConnections()) ?? [];
      const connected = rows.filter((a) => a.status === "connected");
      setAccounts(connected);
      // Preselect when exactly one connected account exists.
      setSelected((prev) => {
        if (prev && connected.some((a) => a.unipile_account_id === prev)) return prev;
        return connected.length === 1 ? connected[0].unipile_account_id : "";
      });
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not load your LinkedIn connections."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAccounts();
  }, [loadAccounts]);

  const handleLaunch = async () => {
    if (!campaignId || !selected) return;
    setLaunching(true);
    setError(null);
    try {
      await linkedinApi.launch(campaignId, selected);
      setLaunched(true);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Launch failed. Please try again."
      );
    } finally {
      setLaunching(false);
    }
  };

  const noPosts = postCount === 0;
  const noAccounts = !loading && accounts.length === 0;
  const canLaunch =
    !!campaignId && !!selected && !noPosts && !launching && !launched;

  if (launched) {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-4 py-3 text-xs text-emerald-300">
        <CheckCircle2 size={16} className="shrink-0" />
        <span>
          Campaign launched. Scheduled posts are bound to your LinkedIn account —
          track live progress in the{" "}
          <Link href="/prospects" className="underline hover:text-emerald-200">
            Autopilot Control Room
          </Link>
          .
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {error && (
        <div className="flex items-start gap-2 rounded-lg bg-[#ef4444]/10 border border-[#ef4444]/20 px-3 py-2 text-[11px] text-[#f87171]">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-[11px] text-[#9AA6B2] py-1">
          <Loader2 size={14} className="animate-spin" />
          Loading your LinkedIn accounts…
        </div>
      ) : noAccounts ? (
        <div className="flex items-center justify-between gap-3 rounded-lg border border-dashed border-white/[0.12] px-3 py-2.5">
          <span className="text-[11px] text-[#9AA6B2]">
            No LinkedIn account connected. Connect one to launch.
          </span>
          <Link
            href="/prospects"
            className="inline-flex items-center gap-1.5 rounded-md bg-[#00c2ee] hover:bg-[#00a9d0] text-[#0E141B] text-[11px] font-semibold px-3 py-1.5 transition-colors"
          >
            <Plug size={13} />
            Connect LinkedIn
          </Link>
        </div>
      ) : accounts.length > 1 ? (
        <label className="block space-y-1">
          <span className="text-[11px] text-[#9AA6B2]">
            Publish from this LinkedIn account
          </span>
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            className="w-full rounded-lg bg-[#0E141B] border border-white/[0.12] px-3 py-2 text-xs text-[#F5F7FA] focus:border-[#00c2ee] focus:outline-none"
          >
            <option value="" disabled>
              Select an account…
            </option>
            {accounts.map((a) => (
              <option key={a.id} value={a.unipile_account_id}>
                {a.provider} • {a.unipile_account_id}
              </option>
            ))}
          </select>
        </label>
      ) : (
        <div className="flex items-center gap-2 rounded-lg bg-white/[0.04] border border-white/[0.08] px-3 py-2 text-[11px] text-[#9AA6B2]">
          <CheckCircle2 size={13} className="text-emerald-400 shrink-0" />
          <span>
            Publishing from{" "}
            <span className="text-[#F5F7FA] font-medium">
              {accounts[0].provider}
            </span>{" "}
            account{" "}
            <span className="font-mono text-[#6B7785]">
              {accounts[0].unipile_account_id}
            </span>
          </span>
        </div>
      )}

      <button
        type="button"
        disabled={!canLaunch}
        onClick={handleLaunch}
        className={`w-full py-2.5 px-4 rounded-lg text-white text-xs font-semibold flex items-center justify-center gap-2 shadow-lg transition-all ${canLaunch
          ? "bg-gradient-to-r from-[#0a66c2] to-[#0077b5] hover:from-[#0077b5] hover:to-[#0a66c2] hover:shadow-cyan-500/20 cursor-pointer"
          : "bg-[#272F38] text-[#6B7785] cursor-not-allowed opacity-60"
          }`}
      >
        {launching ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <Rocket size={14} />
        )}
        <span>
          {noPosts
            ? "Generate posts to launch"
            : "LAUNCH AUTOPILOT CAMPAIGN"}
        </span>
      </button>
    </div>
  );
}

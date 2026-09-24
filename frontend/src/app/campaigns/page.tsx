"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus, Megaphone, Loader2, AlertCircle, Calendar, ArrowRight, RefreshCw } from "lucide-react";
import Sidebar from "@/components/shell/Sidebar";
import { useAuth } from "@/context/AuthContext";
import { useBrand } from "@/context/BrandContext";
import { campaignApi, Campaign } from "@/lib/api";

function formatDate(isoString?: string): string {
  if (!isoString) return "-";
  try {
    const d = new Date(isoString);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return isoString;
  }
}

function StatusBadge({ state }: { state?: string }) {
  const s = (state || "Draft").toUpperCase();
  let bg = "bg-[#EDF6F9] text-[#187CA4] border-[#DCE6EC]";
  if (s === "DRAFT") {
    bg = "bg-[#F1F3F5] text-[#52606B] border-[#DCE6EC]";
  } else if (s === "PUBLISHED") {
    bg = "bg-[#EBFBEE] text-[#2B8A3E] border-[#C3FAC7]";
  } else if (s === "ARCHIVED") {
    bg = "bg-[#F8F9FA] text-[#868E96] border-[#E9ECEF]";
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border uppercase tracking-wider ${bg}`}
    >
      {state || "Draft"}
    </span>
  );
}

export default function CampaignsPage() {
  const { user, isLoading: authLoading, setIsAuthModalOpen } = useAuth();
  const { activeBrand, activeBrandId, isLoading: brandsLoading } = useBrand();
  const router = useRouter();

  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshIndex, setRefreshIndex] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (authLoading || brandsLoading) return;
      if (!user) {
        setLoading(false);
        return;
      }

      if (!activeBrandId) {
        setCampaigns([]);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const res = await campaignApi.list({
          company_profile_id: activeBrandId,
          page_size: 50,
        });
        if (cancelled) return;

        setCampaigns(res.campaigns || []);
      } catch (err: unknown) {
        if (!cancelled) {
          const msg = err instanceof Error ? err.message : "Failed to load campaigns";
          setError(msg);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [authLoading, brandsLoading, user, activeBrandId, refreshIndex]);

  return (
    <div className="flex h-screen bg-[#F8FBFC] text-[#18222D] overflow-hidden font-sans">
      <Sidebar active="campaigns" />

      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Top Header */}
        <header className="h-16 shrink-0 border-b border-[#DCE6EC] bg-white flex items-center justify-between px-6 sm:px-8">
          <div className="min-w-0">
            <h1 className="text-[18px] font-semibold text-[#18222D] flex items-center gap-2">
              <Megaphone size={18} className="text-[#187CA4]" />
              Campaigns
            </h1>
            <p className="text-[12px] text-[#52606B] truncate">
              {activeBrand
                ? `Showing campaigns for ${activeBrand.company_name}`
                : "Select or set up a brand to view campaigns"}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setRefreshIndex((i) => i + 1)}
              aria-label="Refresh campaigns"
              className="p-2 text-[#52606B] hover:text-[#18222D] hover:bg-[#F8FBFC] rounded-[8px] border border-[#DCE6EC] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#187CA4]/30"
            >
              <RefreshCw size={15} />
            </button>
            <button
              type="button"
              onClick={() => {
                if (!user) {
                  setIsAuthModalOpen(true);
                  return;
                }
                router.push("/new-campaign");
              }}
              className="inline-flex items-center gap-2 rounded-[8px] bg-[#187CA4] hover:bg-[#136384] text-white text-[13.5px] font-semibold px-4 py-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#187CA4]/40"
            >
              <Plus size={16} /> Create Campaign
            </button>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 p-6 sm:p-8 max-w-5xl w-full mx-auto">
          {/* State: Loading */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-20 text-[#52606B]">
              <Loader2 size={24} className="animate-spin text-[#187CA4] mb-3" />
              <p className="text-[13.5px]">Loading campaigns…</p>
            </div>
          )}

          {/* State: Error */}
          {!loading && error && (
            <div className="rounded-[12px] border border-[#F5C6CB] bg-[#FDF7F7] p-5 text-[#721C24] flex items-start gap-3">
              <AlertCircle size={20} className="shrink-0 mt-0.5 text-[#DC3545]" />
              <div className="flex-1 min-w-0">
                <p className="text-[14px] font-medium">Failed to load campaigns</p>
                <p className="text-[13px] text-[#721C24]/80 mt-1">{error}</p>
                <button
                  type="button"
                  onClick={() => setRefreshIndex((i) => i + 1)}
                  className="mt-3 text-[13px] font-semibold underline text-[#187CA4] hover:text-[#136384]"
                >
                  Retry
                </button>
              </div>
            </div>
          )}

          {/* State: No Active Brand */}
          {!loading && !error && !activeBrand && (
            <div className="rounded-[12px] border border-[#DCE6EC] bg-white p-10 text-center shadow-sm">
              <Megaphone size={36} className="text-[#5BC0EB] mx-auto mb-3" />
              <h2 className="text-[16px] font-semibold text-[#18222D]">No brand profile selected</h2>
              <p className="text-[13.5px] text-[#52606B] mt-1 max-w-sm mx-auto">
                Set up a brand first to manage and generate campaigns.
              </p>
              <Link
                href="/brandsetup?mode=new"
                className="mt-5 inline-flex items-center gap-2 rounded-[8px] bg-[#187CA4] hover:bg-[#136384] text-white text-[13.5px] font-semibold px-4 py-2 transition-colors"
              >
                Set up brand
              </Link>
            </div>
          )}

          {/* State: Empty */}
          {!loading && !error && activeBrand && campaigns.length === 0 && (
            <div className="rounded-[12px] border border-[#DCE6EC] bg-white p-12 text-center shadow-sm">
              <div className="w-12 h-12 rounded-full bg-[#EDF6F9] text-[#187CA4] grid place-items-center mx-auto mb-4">
                <Megaphone size={22} />
              </div>
              <h2 className="text-[17px] font-semibold text-[#18222D]">No campaigns yet for this brand</h2>
              <p className="text-[13.5px] text-[#52606B] mt-1 max-w-sm mx-auto">
                Start your first campaign for {activeBrand.company_name} to generate tailored LinkedIn strategy and content.
              </p>
              <div className="mt-6">
                <button
                  type="button"
                  onClick={() => router.push("/new-campaign")}
                  className="inline-flex items-center gap-2 rounded-[8px] bg-[#187CA4] hover:bg-[#136384] text-white text-[14px] font-semibold px-5 py-2.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#187CA4]/40"
                >
                  <Plus size={16} /> Create Campaign
                </button>
              </div>
            </div>
          )}

          {/* State: Populated */}
          {!loading && !error && activeBrand && campaigns.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1 pb-1">
                <p className="text-[13px] font-medium text-[#52606B]">
                  {campaigns.length} {campaigns.length === 1 ? "campaign" : "campaigns"}
                </p>
              </div>

              <div className="divide-y divide-[#DCE6EC] rounded-[12px] border border-[#DCE6EC] bg-white shadow-sm overflow-hidden">
                {campaigns.map((c) => (
                  <div
                    key={c.id}
                    onClick={() => router.push(`/campaigns/${c.id}`)}
                    className="p-4 sm:p-5 flex items-center justify-between gap-4 hover:bg-[#F8FBFC] cursor-pointer transition-colors group"
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        router.push(`/campaigns/${c.id}`);
                      }
                    }}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <span className="text-[15px] font-semibold text-[#18222D] group-hover:text-[#187CA4] transition-colors truncate">
                          {c.name || "Untitled Campaign"}
                        </span>
                        <StatusBadge state={c.state} />
                      </div>
                      <div className="flex items-center gap-4 text-[12px] text-[#52606B]">
                        <span className="flex items-center gap-1.5">
                          <Calendar size={13} className="text-[#52606B]/70" />
                          Created {formatDate(c.created_at)}
                        </span>
                        {c.platforms && c.platforms.length > 0 && (
                          <span className="truncate">
                            {c.platforms.map((p) => p.charAt(0).toUpperCase() + p.slice(1)).join(", ")}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="shrink-0 flex items-center text-[#52606B] group-hover:text-[#187CA4] transition-colors">
                      <ArrowRight size={17} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

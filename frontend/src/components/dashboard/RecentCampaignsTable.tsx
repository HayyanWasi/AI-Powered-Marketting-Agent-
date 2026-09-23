"use client";

import { useState, useEffect } from "react";
import { Search, ExternalLink, RotateCcw } from "lucide-react";
import { campaignApi, Campaign } from "@/lib/api";
import CampaignDetailsModal from "@/components/campaign/CampaignDetailsModal";

type DisplayStatus = "Running" | "Completed" | "Optimizing" | "Scheduled" | "Draft" | "Archived";

interface DisplayRow {
  id: string;
  name: string;
  channel: string;
  agentInitial: string;
  agentName: string;
  agentRole: string;
  executedAt: string;
  status: DisplayStatus;
  platforms: string;
}

function stateToDisplayStatus(state: string): DisplayStatus {
  const map: Record<string, DisplayStatus> = {
    Active: "Running",
    Running: "Running",
    Draft: "Draft",
    Scheduled: "Scheduled",
    Completed: "Completed",
    Archived: "Archived",
    Paused: "Optimizing",
    Optimizing: "Optimizing",
  };
  return map[state] ?? "Draft";
}

function relativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function campaignToRow(c: Campaign): DisplayRow {
  const platformLabels = (c.platforms || [])
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join(" • ");

  return {
    id: c.id,
    name: c.name,
    channel: platformLabels || "Multi-channel",
    agentInitial: c.name.charAt(0).toUpperCase(),
    agentName: "AI Agent",
    agentRole: "Campaign Execution",
    executedAt: relativeTime(c.updated_at || c.created_at),
    status: stateToDisplayStatus(c.state),
    platforms: platformLabels,
  };
}

function TableSkeleton() {
  return (
    <div className="rounded-lg bg-[#11161D] border border-[#252C35] overflow-hidden animate-pulse">
      <div className="p-4 sm:p-5 border-b border-[#252C35]">
        <div className="h-4 w-48 bg-[#252C35] rounded mb-2" />
        <div className="h-3 w-72 bg-[#1e262f] rounded" />
      </div>
      <div className="divide-y divide-[#252C35]">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className="flex items-center gap-4 px-4 py-3">
            <div className="h-3 w-48 bg-[#252C35] rounded" />
            <div className="h-3 w-24 bg-[#1e262f] rounded" />
            <div className="h-3 w-16 bg-[#252C35] rounded" />
            <div className="h-3 w-16 bg-[#1e262f] rounded ml-auto" />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function RecentCampaignsTable() {
  const [rows, setRows] = useState<DisplayRow[] | null>(null);
  const [total, setTotal] = useState(0);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState("All");
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const [selectedCampaignName, setSelectedCampaignName] = useState<string | undefined>(undefined);

  useEffect(() => {
    async function fetchCampaigns() {
      try {
        const res = await campaignApi.list({ page_size: 20 });
        setRows(res.campaigns.map(campaignToRow));
        setTotal(res.total);
      } catch {
        setRows([]);
      }
    }
    fetchCampaigns();
  }, []);

  if (rows === null) return <TableSkeleton />;

  const filteredData = rows.filter((item) => {
    const matchesSearch =
      item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.channel.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus =
      filterStatus === "All" || item.status === filterStatus;

    return matchesSearch && matchesStatus;
  });

  return (
    <div className="rounded-lg bg-[#11161D] border border-[#252C35] overflow-hidden">
      {/* Top Header & Search / Filter Controls */}
      <div className="p-4 sm:p-5 border-b border-[#252C35] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-[#F3F4F6]">
            Campaign Registry
          </h2>
          <p className="text-xs text-[#9CA3AF] mt-0.5">
            All campaigns from Supabase database — {total} total
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Status Filter */}
          <div className="flex items-center space-x-1 p-0.5 rounded-md bg-[#171D25] border border-[#252C35]">
            {["All", "Running", "Draft", "Completed"].map((status) => (
              <button
                key={status}
                type="button"
                onClick={() => setFilterStatus(status)}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${filterStatus === status
                    ? "bg-[#252C35] text-[#F3F4F6]"
                    : "text-[#9CA3AF] hover:text-[#F3F4F6]"
                  }`}
              >
                {status}
              </button>
            ))}
          </div>

          {/* Search Box */}
          <div className="relative">
            <Search
              size={13}
              className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#6B7280]"
            />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search campaigns..."
              className="pl-8 pr-3 py-1.5 rounded-md bg-[#171D25] border border-[#252C35] text-xs text-[#F3F4F6] placeholder-[#6B7280] focus:outline-none focus:border-[#3B82F6] transition-colors w-44 sm:w-52"
            />
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#252C35] bg-[#171D25]/40 text-[11px] font-medium text-[#9CA3AF] uppercase tracking-wider">
              <th className="py-2.5 px-4">Campaign & Channel</th>
              <th className="py-2.5 px-4">Platforms</th>
              <th className="py-2.5 px-4">Status</th>
              <th className="py-2.5 px-4">Last Updated</th>
              <th className="py-2.5 px-4 text-right">Action</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-[#252C35] text-xs text-[#9CA3AF]">
            {filteredData.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-[#6B7280] text-xs">
                  {searchTerm || filterStatus !== "All"
                    ? "No campaigns match your filter."
                    : "No campaigns yet. Create your first campaign →"}
                </td>
              </tr>
            ) : (
              filteredData.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => {
                    setSelectedCampaignId(item.id);
                    setSelectedCampaignName(item.name);
                  }}
                  className="hover:bg-[#171D25]/70 transition-colors cursor-pointer group"
                >
                  {/* Campaign Name & Channel */}
                  <td className="py-3 px-4">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedCampaignId(item.id);
                        setSelectedCampaignName(item.name);
                      }}
                      className="font-medium text-[#F3F4F6] hover:text-[#3B82F6] hover:underline text-xs leading-snug text-left cursor-pointer transition-colors"
                    >
                      {item.name}
                    </button>
                    <div className="text-[11px] text-[#6B7280] mt-0.5">
                      {item.channel}
                    </div>
                  </td>

                  {/* Platforms */}
                  <td className="py-3 px-4">
                    <div className="flex items-center space-x-2">
                      <div className="w-5 h-5 rounded-full bg-[#252C35] text-[#F3F4F6] text-[10px] font-medium flex items-center justify-center flex-shrink-0">
                        {item.agentInitial}
                      </div>
                      <span className="text-[#9CA3AF] text-[11px] truncate max-w-[120px]">
                        {item.platforms}
                      </span>
                    </div>
                  </td>

                  {/* Status */}
                  <td className="py-3 px-4">
                    <span className="inline-flex items-center text-xs">
                      {item.status === "Running" && (
                        <>
                          <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] mr-1.5 animate-pulse" />
                          <span className="text-[#F3F4F6]">Running</span>
                        </>
                      )}
                      {item.status === "Draft" && (
                        <>
                          <span className="w-1.5 h-1.5 rounded-full bg-[#3B82F6] mr-1.5" />
                          <span className="text-[#F3F4F6]">Draft</span>
                        </>
                      )}
                      {item.status === "Optimizing" && (
                        <>
                          <span className="w-1.5 h-1.5 rounded-full bg-[#3B82F6] mr-1.5" />
                          <span className="text-[#F3F4F6]">Optimizing</span>
                        </>
                      )}
                      {item.status === "Scheduled" && (
                        <>
                          <span className="w-1.5 h-1.5 rounded-full bg-[#F59E0B] mr-1.5" />
                          <span className="text-[#F3F4F6]">Scheduled</span>
                        </>
                      )}
                      {item.status === "Completed" && (
                        <>
                          <span className="w-1.5 h-1.5 rounded-full bg-[#6B7280] mr-1.5" />
                          <span className="text-[#9CA3AF]">Completed</span>
                        </>
                      )}
                      {item.status === "Archived" && (
                        <>
                          <span className="w-1.5 h-1.5 rounded-full bg-[#6B7280] mr-1.5" />
                          <span className="text-[#6B7280]">Archived</span>
                        </>
                      )}
                    </span>
                  </td>

                  {/* Last Updated */}
                  <td className="py-3 px-4 text-[#9CA3AF] text-[11px] whitespace-nowrap">
                    {item.executedAt}
                  </td>

                  {/* Actions */}
                  <td className="py-3 px-4 text-right whitespace-nowrap">
                    <div className="inline-flex items-center space-x-2">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedCampaignId(item.id);
                          setSelectedCampaignName(item.name);
                        }}
                        className="p-1 rounded text-[#9CA3AF] hover:text-[#3B82F6] hover:bg-[#252C35] transition-colors cursor-pointer"
                        title="View Details"
                      >
                        <ExternalLink size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="p-3 px-4 border-t border-[#252C35] bg-[#171D25]/30 flex items-center justify-between text-xs text-[#6B7280]">
        <span>
          Showing {filteredData.length} of {total} campaigns
        </span>
        <span>Live from Supabase</span>
      </div>

      {/* Campaign Details Modal */}
      <CampaignDetailsModal
        campaignId={selectedCampaignId}
        initialCampaignName={selectedCampaignName}
        isOpen={!!selectedCampaignId}
        onClose={() => setSelectedCampaignId(null)}
      />
    </div>
  );
}

"use client";

import { useState } from "react";
import Link from "next/link";
import { Plus, RefreshCw, Calendar } from "lucide-react";

export default function DashboardHeader() {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [timeRange, setTimeRange] = useState("Last 30 Days");

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 800);
  };

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-[#252C35]">
      {/* Title & Status */}
      <div>
        <div className="flex items-center space-x-2.5 mb-1.5">
          <span className="inline-flex items-center space-x-1.5 text-xs text-[#9CA3AF]">
            <span className="w-2 h-2 rounded-full bg-[#10B981]" />
            <span>Operational Cluster Active</span>
          </span>
        </div>

        <h1 className="text-xl sm:text-2xl font-semibold text-[#F3F4F6] tracking-tight">
          Executive Operations
        </h1>
        <p className="text-xs text-[#9CA3AF] mt-0.5 max-w-xl">
          Real-time metrics across active commercial campaigns, multimodal generations, and system throughput.
        </p>
      </div>

      {/* Action Controls */}
      <div className="flex items-center space-x-2.5 self-start sm:self-auto">
        {/* Date range toggle */}
        <div className="relative inline-flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-[#11161D] border border-[#252C35] text-xs text-[#F3F4F6] hover:bg-[#171D25] transition-colors">
          <Calendar size={13} className="text-[#9CA3AF]" />
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="bg-transparent text-[#F3F4F6] focus:outline-none cursor-pointer pr-1 text-xs"
          >
            <option value="Last 24 Hours" className="bg-[#11161D] text-[#F3F4F6]">
              Last 24 Hours
            </option>
            <option value="Last 7 Days" className="bg-[#11161D] text-[#F3F4F6]">
              Last 7 Days
            </option>
            <option value="Last 30 Days" className="bg-[#11161D] text-[#F3F4F6]">
              Last 30 Days
            </option>
            <option value="This Quarter" className="bg-[#11161D] text-[#F3F4F6]">
              This Quarter
            </option>
          </select>
        </div>

        {/* Refresh button */}
        <button
          type="button"
          onClick={handleRefresh}
          className="p-2 rounded-lg bg-[#11161D] border border-[#252C35] text-[#9CA3AF] hover:text-[#F3F4F6] hover:bg-[#171D25] transition-colors cursor-pointer"
          title="Refresh Metrics"
          aria-label="Refresh Metrics"
        >
          <RefreshCw
            size={14}
            className={isRefreshing ? "animate-spin text-[#3B82F6]" : ""}
          />
        </button>

        {/* Primary CTA: Launch New Campaign */}
        <Link
          href="/new-campaign"
          className="px-3.5 py-1.5 rounded-lg bg-[#3B82F6] hover:bg-[#2563EB] text-white text-xs font-medium transition-colors flex items-center space-x-1.5 shadow-sm"
        >
          <Plus size={14} />
          <span>New Campaign</span>
        </Link>
      </div>
    </div>
  );
}

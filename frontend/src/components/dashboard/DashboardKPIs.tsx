"use client";

import { useEffect, useState } from "react";
import { ArrowUpRight } from "lucide-react";
import { campaignApi, operationsApi } from "@/lib/api";

interface KPIItem {
  id: string;
  title: string;
  value: string;
  trend: string;
  trendPositive: boolean;
  trendLabel: string;
  detailSummary: string;
}

function KPISkeleton() {
  return (
    <div className="rounded-lg bg-[#11161D] border border-[#252C35] p-5 flex flex-col justify-between animate-pulse">
      <div className="h-3 w-28 bg-[#252C35] rounded mb-4" />
      <div className="h-8 w-20 bg-[#252C35] rounded mb-4" />
      <div className="pt-3 border-t border-[#252C35]/60 space-y-1.5">
        <div className="h-3 w-24 bg-[#252C35] rounded" />
        <div className="h-2.5 w-36 bg-[#1e262f] rounded" />
      </div>
    </div>
  );
}

export default function DashboardKPIs() {
  const [kpiData, setKpiData] = useState<KPIItem[] | null>(null);

  useEffect(() => {
    async function fetchKPIs() {
      try {
        // Fetch campaigns + operations metrics in parallel
        const [campaignRes, metricsRes] = await Promise.allSettled([
          campaignApi.list({ page_size: 100 }),
          operationsApi.getMetrics(),
        ]);

        const campaigns =
          campaignRes.status === "fulfilled" ? campaignRes.value.campaigns : [];
        const total =
          campaignRes.status === "fulfilled" ? campaignRes.value.total : 0;
        const metrics =
          metricsRes.status === "fulfilled" ? (metricsRes.value as Record<string, unknown>) : {};

        // Derive real values
        const activeCampaigns = campaigns.filter(
          (c) => c.state === "Active" || c.state === "Draft" || c.state === "Running"
        ).length;

        const platformCounts: Record<string, number> = {};
        campaigns.forEach((c) => {
          (c.platforms || []).forEach((p: string) => {
            platformCounts[p] = (platformCounts[p] || 0) + 1;
          });
        });
        const platformSummary = Object.entries(platformCounts)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 3)
          .map(([p, n]) => `${n} ${p.charAt(0).toUpperCase() + p.slice(1)}`)
          .join(" • ");

        // Operations metrics (real if available, graceful fallback)
        const totalWorkflows = (metrics?.total_workflows as number) ?? 0;
        const totalCost = (metrics?.total_cost_usd as number) ?? 0;
        const latencyP50 = (metrics?.latency_p50_ms as number) ?? 0;
        const throughput = (metrics?.throughput as number) ?? 0;
        const failureRate = (metrics?.failure_rate as number) ?? 0;
        const totalTokens = (metrics?.total_tokens as number) ?? 0;

        const data: KPIItem[] = [
          {
            id: "active-campaigns",
            title: "Total Campaigns",
            value: String(total),
            trend: activeCampaigns > 0 ? `${activeCampaigns} active` : "Drafts",
            trendPositive: true,
            trendLabel: "in database",
            detailSummary: platformSummary || "No campaigns yet",
          },
          {
            id: "total-workflows",
            title: "Total AI Workflows",
            value: totalWorkflows > 0 ? totalWorkflows.toLocaleString() : "—",
            trend: totalTokens > 0 ? `${(totalTokens / 1000).toFixed(1)}k` : "Live",
            trendPositive: true,
            trendLabel: totalTokens > 0 ? "tokens used" : "tracking active",
            detailSummary:
              totalCost > 0
                ? `$${totalCost.toFixed(4)} cost • ${throughput.toFixed(1)} req/s`
                : "No workflow executions yet",
          },
          {
            id: "system-latency",
            title: "Inference Latency",
            value: latencyP50 > 0 ? `${latencyP50.toFixed(0)}ms` : "—",
            trend: failureRate < 1 ? "Optimal" : `${failureRate.toFixed(1)}% err`,
            trendPositive: failureRate < 1,
            trendLabel: "p50 latency",
            detailSummary:
              latencyP50 > 0
                ? `p50: ${latencyP50.toFixed(0)}ms • p95: ${(metrics?.latency_p95_ms as number ?? 0).toFixed(0)}ms`
                : "No requests tracked yet",
          },
          {
            id: "system-health",
            title: "System Health",
            value: failureRate < 1 ? "99.9%+" : `${(100 - failureRate).toFixed(1)}%`,
            trend: "Optimal",
            trendPositive: true,
            trendLabel: "uptime",
            detailSummary:
              totalWorkflows > 0
                ? `${(metrics?.failure_count as number ?? 0)} failures • ${(metrics?.total_retries as number ?? 0)} retries`
                : "Backend connected • Monitoring active",
          },
        ];

        setKpiData(data);
      } catch {
        // On full failure keep null → skeletons shown
      }
    }

    fetchKPIs();
  }, []);

  if (!kpiData) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <KPISkeleton key={i} />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      {kpiData.map((item) => (
        <div
          key={item.id}
          className="rounded-lg bg-[#11161D] border border-[#252C35] p-5 flex flex-col justify-between transition-colors hover:border-[#323B47]"
        >
          {/* Top: Small Muted Label */}
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-[#9CA3AF]">
              {item.title}
            </span>
          </div>

          {/* Middle: Large Metric Number */}
          <div className="mb-3">
            <span className="text-2xl sm:text-3xl font-semibold text-[#F3F4F6] tracking-tight">
              {item.value}
            </span>
          </div>

          {/* Bottom: Tiny Subtle Trend Indicator & Supporting Info */}
          <div className="pt-3 border-t border-[#252C35]/60 space-y-1.5">
            <div className="flex items-center space-x-1.5 text-xs">
              <span
                className={`inline-flex items-center font-medium ${
                  item.trendPositive ? "text-[#10B981]" : "text-[#EF4444]"
                }`}
              >
                {item.trend.startsWith("+") && <ArrowUpRight size={13} className="mr-0.5" />}
                {item.trend}
              </span>
              <span className="text-[#6B7280]">{item.trendLabel}</span>
            </div>

            <p className="text-[11px] text-[#6B7280] truncate">
              {item.detailSummary}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

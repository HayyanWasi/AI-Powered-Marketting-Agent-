"use client";

import { Suspense, useCallback, useEffect, useState, useMemo } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import Sidebar from "@/components/shell/Sidebar";
import { useAuth } from "@/context/AuthContext";
import { useBrand } from "@/context/BrandContext";
import {
  autopilotApi,
  UnifiedActivityEvent,
  UnifiedActivityParams,
} from "@/lib/api";
import {
  Clock,
  RefreshCw,
  Filter,
  Send,
  ThumbsUp,
  MessageSquare,
  UserPlus,
  CheckCircle2,
  AlertCircle,
  XCircle,
  Calendar,
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  Image as ImageIcon,
  Copy,
  Check,
  Loader2,
  Building2,
  X,
} from "lucide-react";

const PAGE_SIZE = 25;
const MAX_OFFSET = 1000;

const VALID_SOURCES = ["all", "publishing", "engagement"] as const;
type SourceFilter = (typeof VALID_SOURCES)[number];

const VALID_ACTIONS = [
  "all",
  "post",
  "like",
  "comment",
  "connection_request",
] as const;
type ActionFilter = (typeof VALID_ACTIONS)[number];

const VALID_STATUSES = [
  "all",
  "published",
  "succeeded",
  "publishing",
  "claimed",
  "needs_review",
  "failed",
  "scheduled",
  "draft",
] as const;
type StatusFilter = (typeof VALID_STATUSES)[number];

function formatRelativeTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    if (diffMs < 0) {
      const absDiff = Math.abs(diffMs);
      const diffMins = Math.floor(absDiff / 60000);
      if (diffMins < 60) return `in ${diffMins}m`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `in ${diffHours}h`;
      const diffDays = Math.floor(diffHours / 24);
      return `in ${diffDays}d`;
    }
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch {
    return isoString;
  }
}

function formatAbsoluteTime(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return isoString;
  }
}

function StatusBadge({ status }: { status: string }) {
  const s = status.toLowerCase();

  if (s === "published" || s === "succeeded") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11.5px] font-semibold bg-[#EBFBEE] text-[#2B8A3E] border border-[#C3FAC7]">
        <CheckCircle2 size={12} className="shrink-0" />
        {status}
      </span>
    );
  }
  if (s === "publishing" || s === "claimed") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11.5px] font-semibold bg-[#E0F2FE] text-[#0369A1] border border-[#BAE6FD]">
        <Clock size={12} className="shrink-0" />
        {status}
      </span>
    );
  }
  if (s === "scheduled") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11.5px] font-semibold bg-[#EEF2FF] text-[#4F46E5] border border-[#E0E7FF]">
        <Calendar size={12} className="shrink-0" />
        scheduled
      </span>
    );
  }
  if (s === "needs_review") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11.5px] font-semibold bg-[#FEF3C7] text-[#B45309] border border-[#FDE68A]">
        <AlertCircle size={12} className="shrink-0" />
        needs_review
      </span>
    );
  }
  if (s === "failed") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11.5px] font-semibold bg-[#FDF7F7] text-[#DC3545] border border-[#F5C6CB]">
        <XCircle size={12} className="shrink-0" />
        failed
      </span>
    );
  }

  // draft or other neutral
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[11.5px] font-medium bg-[#F1F3F5] text-[#52606B] border border-[#DCE6EC]">
      {status}
    </span>
  );
}

function ActionIcon({
  action,
  source,
}: {
  action: string;
  source: string;
}) {
  if (action === "post" || source === "publishing") {
    return <Send size={15} className="text-[#187CA4] shrink-0" />;
  }
  if (action === "like") {
    return <ThumbsUp size={15} className="text-[#2563eb] shrink-0" />;
  }
  if (action === "comment") {
    return <MessageSquare size={15} className="text-[#16a34a] shrink-0" />;
  }
  if (action === "connection_request") {
    return <UserPlus size={15} className="text-[#7c3aed] shrink-0" />;
  }
  return <Clock size={15} className="text-[#52606B] shrink-0" />;
}

function actionHumanLabel(action: string, source: string): string {
  if (action === "post" || source === "publishing") return "Publish Post";
  if (action === "like") return "LinkedIn Like";
  if (action === "comment") return "LinkedIn Comment";
  if (action === "connection_request") return "Connection Invite";
  return action;
}

function EventRow({
  event,
  brandName,
}: {
  event: UnifiedActivityEvent;
  brandName?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const [copiedId, setCopiedId] = useState(false);

  const copyId = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(event.id);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 1500);
    }
  };

  const previewText =
    event.target_context?.hook_preview ||
    event.message ||
    event.target_context?.target_id ||
    "";

  const hasMedia =
    Boolean(event.target_context?.media_url) ||
    Boolean(event.metadata?.media_type);

  const isWarningStatus =
    event.status === "failed" || event.status === "needs_review";

  return (
    <div className="hover:bg-[#F8FBFC] transition-colors">
      <div
        onClick={() => setExpanded((prev) => !prev)}
        className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer select-none"
      >
        {/* Left: Action Icon, Type, Status, Context preview */}
        <div className="flex items-start gap-3.5 min-w-0 flex-1">
          <div className="w-8 h-8 rounded-lg bg-[#F0F4F8] grid place-items-center shrink-0 mt-0.5">
            <ActionIcon action={event.action_type} source={event.source_type} />
          </div>

          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[13.5px] font-semibold text-[#18222D]">
                {actionHumanLabel(event.action_type, event.source_type)}
              </span>
              <StatusBadge status={event.status} />
              {brandName && (
                <span className="inline-flex items-center gap-1 text-[11px] font-medium text-[#52606B] bg-[#F1F3F5] px-2 py-0.5 rounded">
                  <Building2 size={11} className="text-[#8a949c]" />
                  {brandName}
                </span>
              )}
              {event.target_context?.campaign_name && (
                <span className="text-[11px] font-medium text-[#187CA4] bg-[#EDF6F9] px-2 py-0.5 rounded truncate max-w-[200px]">
                  Campaign: {event.target_context.campaign_name}
                </span>
              )}
            </div>

            {/* Content Preview */}
            {previewText && (
              <p className="text-[13px] text-[#52606B] truncate max-w-2xl">
                {previewText}
              </p>
            )}

            {/* Error snippet if failed/needs_review */}
            {isWarningStatus && event.error_message && (
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#FFF7ED] border border-[#FED7AA] text-[12px] text-[#9A3412]">
                <AlertCircle size={13} className="text-[#EA580C] shrink-0" />
                <span className="truncate max-w-xl">{event.error_message}</span>
              </div>
            )}
          </div>
        </div>

        {/* Right: Timestamp, Media tag, Expand chevron */}
        <div className="flex items-center justify-between sm:justify-end gap-3 shrink-0 sm:pl-3 border-t sm:border-t-0 pt-2 sm:pt-0 border-[#f1f3f5]">
          <div className="flex items-center gap-2">
            {hasMedia && (
              <span
                title="Media attached"
                className="inline-flex items-center gap-1 text-[11.5px] text-[#187CA4] bg-[#EDF6F9] px-2 py-0.5 rounded border border-[#DCE6EC]"
              >
                <ImageIcon size={12} />
                Media
              </span>
            )}
            <span
              title={formatAbsoluteTime(event.timestamp)}
              className="text-[12.5px] text-[#8a949c] whitespace-nowrap"
            >
              {formatRelativeTime(event.timestamp)}
            </span>
          </div>

          <button
            type="button"
            aria-label={expanded ? "Collapse details" : "Expand details"}
            className="p-1 text-[#8a949c] hover:text-[#18222D] transition-colors"
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {/* Expanded Details Drawer */}
      {expanded && (
        <div className="px-4 pb-4 sm:px-5 sm:pb-5 pt-1 border-t border-[#f1f3f5] bg-[#FAFBFD] space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-[12px]">
            <div className="flex items-center justify-between bg-white border border-[#e6e9ec] rounded-md px-3 py-1.5">
              <span className="text-[#8a949c] font-medium">Event ID:</span>
              <div className="flex items-center gap-1.5 font-mono text-[#18222D]">
                <span>{event.id.slice(0, 10)}…</span>
                <button
                  type="button"
                  onClick={copyId}
                  title="Copy full event ID"
                  className="text-[#8a949c] hover:text-[#187CA4]"
                >
                  {copiedId ? (
                    <Check size={12} className="text-[#2B8A3E]" />
                  ) : (
                    <Copy size={12} />
                  )}
                </button>
              </div>
            </div>

            {event.target_context?.target_id && (
              <div className="flex items-center justify-between bg-white border border-[#e6e9ec] rounded-md px-3 py-1.5">
                <span className="text-[#8a949c] font-medium">Target ID:</span>
                <span className="font-mono text-[#18222D] truncate max-w-[160px]">
                  {event.target_context.target_id}
                </span>
              </div>
            )}

            {event.linkedin_account_id && (
              <div className="flex items-center justify-between bg-white border border-[#e6e9ec] rounded-md px-3 py-1.5">
                <span className="text-[#8a949c] font-medium">LinkedIn Acct:</span>
                <span className="font-mono text-[#18222D] truncate max-w-[160px]">
                  {event.linkedin_account_id.slice(0, 8)}…
                </span>
              </div>
            )}

            {event.target_context?.campaign_id && (
              <div className="flex items-center justify-between bg-white border border-[#e6e9ec] rounded-md px-3 py-1.5">
                <span className="text-[#8a949c] font-medium">Campaign ID:</span>
                <span className="font-mono text-[#18222D] truncate max-w-[160px]">
                  {event.target_context.campaign_id.slice(0, 8)}…
                </span>
              </div>
            )}

            {Boolean(event.metadata?.provider_result_id) && (
              <div className="flex items-center justify-between bg-white border border-[#e6e9ec] rounded-md px-3 py-1.5">
                <span className="text-[#8a949c] font-medium">Provider Result:</span>
                <span className="font-mono text-[#18222D] truncate max-w-[160px]">
                  {String(event.metadata?.provider_result_id)}
                </span>
              </div>
            )}

            {Boolean(event.metadata?.slot_id) && (
              <div className="flex items-center justify-between bg-white border border-[#e6e9ec] rounded-md px-3 py-1.5">
                <span className="text-[#8a949c] font-medium">Slot ID:</span>
                <span className="font-mono text-[#18222D] truncate max-w-[160px]">
                  {String(event.metadata?.slot_id)}
                </span>
              </div>
            )}
          </div>

          {/* Full Message / Content Body if available */}
          {event.message && (
            <div className="bg-white border border-[#e6e9ec] rounded-md p-3">
              <span className="text-[11.5px] font-semibold text-[#8a949c] uppercase tracking-wider block mb-1">
                Full Message / Content
              </span>
              <p className="text-[13px] text-[#18222D] whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                {event.message}
              </p>
            </div>
          )}

          {/* Detailed Error message if available */}
          {event.error_message && (
            <div className="bg-[#FFF7ED] border border-[#FED7AA] rounded-md p-3">
              <span className="text-[11.5px] font-semibold text-[#9A3412] uppercase tracking-wider block mb-1">
                Diagnostic Error Details (Sanitized)
              </span>
              <p className="text-[12.5px] text-[#9A3412] font-mono whitespace-pre-wrap">
                {event.error_message}
              </p>
            </div>
          )}

          <div className="text-[11px] text-[#8a949c] flex items-center justify-between pt-1">
            <span>Canonical Timestamp: {formatAbsoluteTime(event.timestamp)}</span>
            <span>Source: {event.source_type}</span>
          </div>
        </div>
      )}
    </div>
  );
}

function HistoryContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { user, isLoading: authLoading } = useAuth();

  // Brands lookup from shared cache
  const { brands } = useBrand();
  const brandMap = useMemo(() => {
    const map: Record<string, string> = {};
    for (const item of brands) {
      map[item.id] = item.company_name;
    }
    return map;
  }, [brands]);

  // Filter States with URL hydration
  const initialBrand = searchParams.get("brand") || "";
  const initialSource = (
    VALID_SOURCES.includes(searchParams.get("source") as SourceFilter)
      ? searchParams.get("source")
      : "all"
  ) as SourceFilter;
  const initialAction = (
    VALID_ACTIONS.includes(searchParams.get("action") as ActionFilter)
      ? searchParams.get("action")
      : "all"
  ) as ActionFilter;
  const initialStatus = (
    VALID_STATUSES.includes(searchParams.get("status") as StatusFilter)
      ? searchParams.get("status")
      : "all"
  ) as StatusFilter;
  const initialFrom = searchParams.get("from") || "";
  const initialTo = searchParams.get("to") || "";
  const initialPage = Math.max(1, parseInt(searchParams.get("page") || "1", 10));

  const [selectedBrand, setSelectedBrand] = useState<string>(initialBrand);
  const [selectedSource, setSelectedSource] = useState<SourceFilter>(initialSource);
  const [selectedAction, setSelectedAction] = useState<ActionFilter>(initialAction);
  const [selectedStatus, setSelectedStatus] = useState<StatusFilter>(initialStatus);
  const [fromDate, setFromDate] = useState<string>(initialFrom);
  const [toDate, setToDate] = useState<string>(initialTo);
  const [page, setPage] = useState<number>(initialPage);

  // Data & loading states
  const [events, setEvents] = useState<UnifiedActivityEvent[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [hasMore, setHasMore] = useState<boolean>(false);
  const [initialLoading, setInitialLoading] = useState<boolean>(true);
  const [fetching, setFetching] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Sync URL search params
  const updateUrlParams = useCallback(
    (updates: {
      brand?: string;
      source?: string;
      action?: string;
      status?: string;
      from?: string;
      to?: string;
      page?: number;
    }) => {
      const p = new URLSearchParams();
      const b = updates.brand !== undefined ? updates.brand : selectedBrand;
      const s = updates.source !== undefined ? updates.source : selectedSource;
      const a = updates.action !== undefined ? updates.action : selectedAction;
      const st = updates.status !== undefined ? updates.status : selectedStatus;
      const f = updates.from !== undefined ? updates.from : fromDate;
      const t = updates.to !== undefined ? updates.to : toDate;
      const pg = updates.page !== undefined ? updates.page : page;

      if (b) p.set("brand", b);
      if (s && s !== "all") p.set("source", s);
      if (a && a !== "all") p.set("action", a);
      if (st && st !== "all") p.set("status", st);
      if (f) p.set("from", f);
      if (t) p.set("to", t);
      if (pg > 1) p.set("page", String(pg));

      const qs = p.toString();
      router.replace(`${pathname}${qs ? `?${qs}` : ""}`, { scroll: false });
    },
    [router, pathname, selectedBrand, selectedSource, selectedAction, selectedStatus, fromDate, toDate, page]
  );



  // Main data fetch function
  const loadHistory = useCallback(async () => {
    if (!user) return;

    setFetching(true);
    setError(null);

    // Calculate offset based on current page
    const offset = Math.min((page - 1) * PAGE_SIZE, MAX_OFFSET);

    // Build ISO timestamp range safely
    let startIso: string | undefined = undefined;
    let endIso: string | undefined = undefined;

    if (fromDate) {
      try {
        startIso = new Date(`${fromDate}T00:00:00`).toISOString();
      } catch {
        /* invalid date */
      }
    }

    if (toDate) {
      try {
        endIso = new Date(`${toDate}T23:59:59.999`).toISOString();
      } catch {
        /* invalid date */
      }
    }

    const params: UnifiedActivityParams = {
      limit: PAGE_SIZE,
      offset,
    };

    if (selectedBrand) params.company_profile_id = selectedBrand;
    if (selectedSource && selectedSource !== "all") params.source_type = selectedSource;
    if (selectedAction && selectedAction !== "all") params.action_type = selectedAction;
    if (selectedStatus && selectedStatus !== "all") params.status = selectedStatus;
    if (startIso) params.start_date = startIso;
    if (endIso) params.end_date = endIso;

    try {
      const res = await autopilotApi.getUnifiedActivity(params);
      setEvents(res.events || []);
      setTotal(res.total || 0);
      setHasMore(res.has_more || false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load history";
      setError(msg);
      setEvents([]);
      setTotal(0);
      setHasMore(false);
    } finally {
      setFetching(false);
      setInitialLoading(false);
    }
  }, [
    user,
    page,
    selectedBrand,
    selectedSource,
    selectedAction,
    selectedStatus,
    fromDate,
    toDate,
  ]);

  // Trigger load whenever filters or page change
  useEffect(() => {
    if (!authLoading && user) {
      const timer = setTimeout(() => {
        void loadHistory();
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [authLoading, user, loadHistory]);

  // Filter change handlers (all reset page to 1)
  const handleBrandChange = (brandId: string) => {
    setSelectedBrand(brandId);
    setPage(1);
    updateUrlParams({ brand: brandId, page: 1 });
  };

  const handleSourceChange = (src: SourceFilter) => {
    setSelectedSource(src);
    // Reset conflicting action if needed
    let nextAction = selectedAction;
    if (src === "publishing" && selectedAction !== "all" && selectedAction !== "post") {
      nextAction = "all";
      setSelectedAction("all");
    } else if (src === "engagement" && selectedAction === "post") {
      nextAction = "all";
      setSelectedAction("all");
    }
    setPage(1);
    updateUrlParams({ source: src, action: nextAction, page: 1 });
  };

  const handleActionChange = (act: ActionFilter) => {
    setSelectedAction(act);
    setPage(1);
    updateUrlParams({ action: act, page: 1 });
  };

  const handleStatusChange = (st: StatusFilter) => {
    setSelectedStatus(st);
    setPage(1);
    updateUrlParams({ status: st, page: 1 });
  };

  const handleFromChange = (val: string) => {
    setFromDate(val);
    setPage(1);
    updateUrlParams({ from: val, page: 1 });
  };

  const handleToChange = (val: string) => {
    setToDate(val);
    setPage(1);
    updateUrlParams({ to: val, page: 1 });
  };

  const handleResetFilters = () => {
    setSelectedBrand("");
    setSelectedSource("all");
    setSelectedAction("all");
    setSelectedStatus("all");
    setFromDate("");
    setToDate("");
    setPage(1);
    updateUrlParams({
      brand: "",
      source: "all",
      action: "all",
      status: "all",
      from: "",
      to: "",
      page: 1,
    });
  };

  // Pagination bounds
  const totalPages = Math.ceil(total / PAGE_SIZE) || 1;
  const currentOffset = (page - 1) * PAGE_SIZE;
  const isCappedAt1000 = currentOffset + PAGE_SIZE >= MAX_OFFSET;
  const canGoNext = hasMore && page < totalPages && !isCappedAt1000;
  const canGoPrev = page > 1;

  const handlePrevPage = () => {
    if (!canGoPrev) return;
    const nextPg = page - 1;
    setPage(nextPg);
    updateUrlParams({ page: nextPg });
  };

  const handleNextPage = () => {
    if (!canGoNext) return;
    const nextPg = page + 1;
    setPage(nextPg);
    updateUrlParams({ page: nextPg });
  };

  const hasActiveFilters =
    Boolean(selectedBrand) ||
    selectedSource !== "all" ||
    selectedAction !== "all" ||
    selectedStatus !== "all" ||
    Boolean(fromDate) ||
    Boolean(toDate);

  return (
    <div className="flex h-screen bg-[#F8FBFC] text-[#18222D] overflow-hidden font-sans">
      <Sidebar active="history" />

      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Standard Sticky Header */}
        <header className="h-16 shrink-0 border-b border-[#DCE6EC] bg-white flex items-center justify-between px-6 sm:px-8 sticky top-0 z-10">
          <div className="min-w-0">
            <h1 className="text-[18px] font-semibold text-[#18222D] flex items-center gap-2">
              <Clock size={18} className="text-[#187CA4]" />
              History
            </h1>
            <p className="text-[12px] text-[#52606B] truncate">
              Unified audit trail of publishing events and engagement actions.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => void loadHistory()}
              disabled={fetching}
              aria-label="Refresh history"
              title="Refresh activity history"
              className="p-2 text-[#52606B] hover:text-[#18222D] hover:bg-[#F8FBFC] rounded-[8px] border border-[#DCE6EC] transition-colors focus-visible:outline-none disabled:opacity-50"
            >
              <RefreshCw
                size={15}
                className={fetching ? "animate-spin text-[#187CA4]" : ""}
              />
            </button>
          </div>
        </header>

        {/* Content Body */}
        <div className="flex-1 p-6 sm:p-8 max-w-5xl w-full mx-auto space-y-5">
          {/* Filter Toolbar */}
          <div className="rounded-[12px] border border-[#DCE6EC] bg-white p-4 shadow-sm space-y-3.5">
            <div className="flex items-center justify-between gap-2 border-b border-[#f1f3f5] pb-2.5">
              <div className="flex items-center gap-2 text-[13px] font-semibold text-[#18222D]">
                <Filter size={15} className="text-[#187CA4]" />
                <span>Filters</span>
              </div>

              {hasActiveFilters && (
                <button
                  type="button"
                  onClick={handleResetFilters}
                  className="text-[12px] font-semibold text-[#187CA4] hover:text-[#136384] transition-colors flex items-center gap-1 cursor-pointer"
                >
                  <X size={13} />
                  Reset filters
                </button>
              )}
            </div>

            {/* Filter Inputs Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              {/* Brand Filter */}
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#7a848c] mb-1">
                  Brand
                </label>
                <select
                  value={selectedBrand}
                  onChange={(e) => handleBrandChange(e.target.value)}
                  className="w-full text-[13px] rounded-md border border-[#DCE6EC] bg-white px-2.5 py-1.5 text-[#18222D] focus:outline-none focus:ring-1 focus:ring-[#187CA4]"
                >
                  <option value="">All Brands</option>
                  {brands.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.company_name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Source Filter */}
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#7a848c] mb-1">
                  Source
                </label>
                <select
                  value={selectedSource}
                  onChange={(e) =>
                    handleSourceChange(e.target.value as SourceFilter)
                  }
                  className="w-full text-[13px] rounded-md border border-[#DCE6EC] bg-white px-2.5 py-1.5 text-[#18222D] focus:outline-none focus:ring-1 focus:ring-[#187CA4]"
                >
                  <option value="all">All Sources</option>
                  <option value="publishing">Publishing</option>
                  <option value="engagement">Engagement</option>
                </select>
              </div>

              {/* Action Filter */}
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#7a848c] mb-1">
                  Action
                </label>
                <select
                  value={selectedAction}
                  onChange={(e) =>
                    handleActionChange(e.target.value as ActionFilter)
                  }
                  className="w-full text-[13px] rounded-md border border-[#DCE6EC] bg-white px-2.5 py-1.5 text-[#18222D] focus:outline-none focus:ring-1 focus:ring-[#187CA4]"
                >
                  <option value="all">All Actions</option>
                  {selectedSource !== "engagement" && (
                    <option value="post">Post</option>
                  )}
                  {selectedSource !== "publishing" && (
                    <>
                      <option value="like">Like</option>
                      <option value="comment">Comment</option>
                      <option value="connection_request">Connection</option>
                    </>
                  )}
                </select>
              </div>

              {/* Status Filter */}
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#7a848c] mb-1">
                  Status
                </label>
                <select
                  value={selectedStatus}
                  onChange={(e) =>
                    handleStatusChange(e.target.value as StatusFilter)
                  }
                  className="w-full text-[13px] rounded-md border border-[#DCE6EC] bg-white px-2.5 py-1.5 text-[#18222D] focus:outline-none focus:ring-1 focus:ring-[#187CA4]"
                >
                  <option value="all">All Statuses</option>
                  <option value="published">published</option>
                  <option value="succeeded">succeeded</option>
                  <option value="publishing">publishing</option>
                  <option value="claimed">claimed</option>
                  <option value="needs_review">needs_review</option>
                  <option value="failed">failed</option>
                  <option value="scheduled">scheduled</option>
                  <option value="draft">draft</option>
                </select>
              </div>

              {/* From Date */}
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#7a848c] mb-1">
                  From Date
                </label>
                <input
                  type="date"
                  value={fromDate}
                  onChange={(e) => handleFromChange(e.target.value)}
                  className="w-full text-[12.5px] rounded-md border border-[#DCE6EC] bg-white px-2 py-1 text-[#18222D] focus:outline-none focus:ring-1 focus:ring-[#187CA4]"
                />
              </div>

              {/* To Date */}
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#7a848c] mb-1">
                  To Date
                </label>
                <input
                  type="date"
                  value={toDate}
                  onChange={(e) => handleToChange(e.target.value)}
                  className="w-full text-[12.5px] rounded-md border border-[#DCE6EC] bg-white px-2 py-1 text-[#18222D] focus:outline-none focus:ring-1 focus:ring-[#187CA4]"
                />
              </div>
            </div>

            {/* Filter Result Summary */}
            <div className="flex items-center justify-between text-[12px] text-[#52606B] pt-1">
              <span>
                Found <strong className="text-[#18222D]">{total}</strong> total{" "}
                {total === 1 ? "event" : "events"} matching criteria
              </span>
              {fetching && !initialLoading && (
                <span className="flex items-center gap-1.5 text-[#187CA4] font-medium">
                  <Loader2 size={13} className="animate-spin" /> Updating results…
                </span>
              )}
            </div>
          </div>

          {/* State: Initial Loading */}
          {initialLoading && (
            <div className="rounded-[12px] border border-[#DCE6EC] bg-white p-14 flex flex-col items-center justify-center text-[#52606B] shadow-sm">
              <Loader2 size={26} className="animate-spin text-[#187CA4] mb-3" />
              <p className="text-[13.5px] font-medium">Loading history…</p>
            </div>
          )}

          {/* State: Error */}
          {!initialLoading && error && (
            <div className="rounded-[12px] border border-[#F5C6CB] bg-[#FDF7F7] p-5 text-[#721C24] flex items-start gap-3 shadow-sm">
              <AlertCircle size={20} className="shrink-0 mt-0.5 text-[#DC3545]" />
              <div className="flex-1 min-w-0">
                <p className="text-[14px] font-semibold">Failed to load history</p>
                <p className="text-[13px] text-[#721C24]/90 mt-1">{error}</p>
                <button
                  type="button"
                  onClick={() => void loadHistory()}
                  className="mt-3 inline-flex items-center gap-1.5 rounded-md bg-[#DC3545] text-white text-[12.5px] font-semibold px-3 py-1.5 hover:bg-[#b91c1c] transition-colors"
                >
                  <RefreshCw size={13} /> Retry
                </button>
              </div>
            </div>
          )}

          {/* State: Global Empty (0 events and no filters active) */}
          {!initialLoading && !error && total === 0 && !hasActiveFilters && (
            <div className="rounded-[12px] border border-[#DCE6EC] bg-white p-12 text-center shadow-sm">
              <div className="w-12 h-12 rounded-full bg-[#EDF6F9] text-[#187CA4] grid place-items-center mx-auto mb-3.5">
                <Clock size={22} />
              </div>
              <h2 className="text-[16px] font-semibold text-[#18222D]">
                No activity recorded yet
              </h2>
              <p className="text-[13px] text-[#52606B] mt-1 max-w-sm mx-auto">
                Scheduled posts, published content, and automated engagement
                events will appear here once executed.
              </p>
            </div>
          )}

          {/* State: Filtered Empty (0 events matching current filters) */}
          {!initialLoading && !error && total === 0 && hasActiveFilters && (
            <div className="rounded-[12px] border border-[#DCE6EC] bg-white p-12 text-center shadow-sm">
              <div className="w-12 h-12 rounded-full bg-[#F1F3F5] text-[#52606B] grid place-items-center mx-auto mb-3.5">
                <Filter size={22} />
              </div>
              <h2 className="text-[16px] font-semibold text-[#18222D]">
                No events match your filters
              </h2>
              <p className="text-[13px] text-[#52606B] mt-1 max-w-sm mx-auto">
                Try clearing or adjusting your status, date range, or action
                type filters to see results.
              </p>
              <div className="mt-5">
                <button
                  type="button"
                  onClick={handleResetFilters}
                  className="inline-flex items-center gap-1.5 rounded-[8px] bg-[#187CA4] hover:bg-[#136384] text-white text-[13px] font-semibold px-4 py-2 transition-colors cursor-pointer"
                >
                  <X size={14} /> Clear filters
                </button>
              </div>
            </div>
          )}

          {/* State: Populated Event List */}
          {!initialLoading && !error && events.length > 0 && (
            <div className="space-y-4">
              <div
                className={`divide-y divide-[#DCE6EC] rounded-[12px] border border-[#DCE6EC] bg-white shadow-sm overflow-hidden transition-opacity ${
                  fetching ? "opacity-60" : "opacity-100"
                }`}
              >
                {events.map((ev) => (
                  <EventRow
                    key={ev.id}
                    event={ev}
                    brandName={
                      ev.company_profile_id
                        ? brandMap[ev.company_profile_id]
                        : undefined
                    }
                  />
                ))}
              </div>

              {/* Offset 1000 Cap Warning */}
              {isCappedAt1000 && (
                <div className="rounded-[8px] border border-[#FED7AA] bg-[#FFFBEB] p-3 text-[12.5px] text-[#9A3412] flex items-center gap-2">
                  <AlertCircle size={15} className="text-[#EA580C] shrink-0" />
                  <span>
                    Maximum viewable window reached (1,000 events). Please narrow
                    your date range to audit older history.
                  </span>
                </div>
              )}

              {/* Pagination Bar */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-2 py-1 text-[13px] text-[#52606B]">
                <div>
                  Showing{" "}
                  <strong className="text-[#18222D]">
                    {currentOffset + 1}
                  </strong>{" "}
                  to{" "}
                  <strong className="text-[#18222D]">
                    {Math.min(currentOffset + events.length, total)}
                  </strong>{" "}
                  of <strong className="text-[#18222D]">{total}</strong> events
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handlePrevPage}
                    disabled={!canGoPrev || fetching}
                    className="inline-flex items-center gap-1 rounded-md border border-[#DCE6EC] bg-white px-3 py-1.5 text-[12.5px] font-medium text-[#18222D] hover:bg-[#F8FBFC] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft size={14} /> Previous
                  </button>

                  <span className="text-[12.5px] px-1 font-medium text-[#18222D]">
                    Page {page} of {totalPages}
                  </span>

                  <button
                    type="button"
                    onClick={handleNextPage}
                    disabled={!canGoNext || fetching}
                    className="inline-flex items-center gap-1 rounded-md border border-[#DCE6EC] bg-white px-3 py-1.5 text-[12.5px] font-medium text-[#18222D] hover:bg-[#F8FBFC] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    Next <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function HistoryLoadingShell() {
  return (
    <div className="flex h-screen bg-[#F8FBFC] text-[#18222D] overflow-hidden font-sans">
      <Sidebar active="history" />
      <main className="flex-1 flex flex-col min-w-0">
        <header className="h-16 shrink-0 border-b border-[#DCE6EC] bg-white flex items-center justify-between px-6 sm:px-8">
          <div className="min-w-0">
            <h1 className="text-[18px] font-semibold text-[#18222D] flex items-center gap-2">
              <Clock size={18} className="text-[#187CA4]" />
              History
            </h1>
            <p className="text-[12px] text-[#52606B]">
              Unified audit trail of publishing events and engagement actions.
            </p>
          </div>
        </header>
        <div className="flex-1 p-6 sm:p-8 max-w-5xl w-full mx-auto flex items-center justify-center">
          <Loader2 size={26} className="animate-spin text-[#187CA4]" />
        </div>
      </main>
    </div>
  );
}

export default function HistoryPage() {
  return (
    <Suspense fallback={<HistoryLoadingShell />}>
      <HistoryContent />
    </Suspense>
  );
}

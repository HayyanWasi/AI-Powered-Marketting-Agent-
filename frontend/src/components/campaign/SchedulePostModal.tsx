"use client";

import { useMemo, useState } from "react";
import { Loader2, AlertCircle, CalendarClock, X } from "lucide-react";

/**
 * Convert a wall-clock date+time in a given IANA timezone to the exact UTC
 * instant, returned as an ISO string with offset (…Z). This is timezone-aware,
 * which the backend requires. No external date library is used.
 */
function zonedWallTimeToIso(
  dateStr: string,
  timeStr: string,
  timeZone: string
): string {
  const [y, mo, d] = dateStr.split("-").map(Number);
  const [h, mi] = timeStr.split(":").map(Number);
  const utcGuess = Date.UTC(y, mo - 1, d, h, mi, 0);
  // How the guessed instant is displayed in the target zone → derive its offset.
  const dtf = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hourCycle: "h23",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  const parts = dtf.formatToParts(new Date(utcGuess));
  const map: Record<string, number> = {};
  for (const p of parts) if (p.type !== "literal") map[p.type] = Number(p.value);
  const asShown = Date.UTC(
    map.year,
    map.month - 1,
    map.day,
    map.hour,
    map.minute,
    map.second
  );
  const offset = asShown - utcGuess; // ms the zone is ahead of UTC
  return new Date(utcGuess - offset).toISOString();
}

const COMMON_ZONES = [
  "UTC",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Berlin",
  "Europe/Madrid",
  "Asia/Karachi",
  "Asia/Dubai",
  "Asia/Kolkata",
  "Asia/Singapore",
  "Asia/Tokyo",
  "Australia/Sydney",
];

function browserZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

interface Props {
  title: string;
  postLabel: string;
  accountName: string;
  /** Existing ISO to prefill (reschedule); undefined for a fresh schedule. */
  initialIso?: string;
  initialTimezone?: string;
  isSaving: boolean;
  error: string | null;
  onConfirm: (isoUtc: string, timezone: string) => void;
  onClose: () => void;
}

export default function SchedulePostModal({
  title,
  postLabel,
  accountName,
  initialIso,
  initialTimezone,
  isSaving,
  error,
  onConfirm,
  onClose,
}: Props) {
  const detected = initialTimezone || browserZone();
  const zones = useMemo(() => {
    const set = new Set<string>([detected, ...COMMON_ZONES]);
    return Array.from(set);
  }, [detected]);

  // Capture "now" once at mount so render stays pure (React 19 purity rule).
  const [mountNow] = useState(() => Date.now());

  const initial = useMemo(() => {
    const base = initialIso ? new Date(initialIso) : new Date(mountNow + 24 * 3600 * 1000);
    // Represent the instant in the chosen zone for the input defaults.
    const dtf = new Intl.DateTimeFormat("en-CA", {
      timeZone: detected,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    });
    const parts: Record<string, string> = {};
    for (const p of dtf.formatToParts(base)) if (p.type !== "literal") parts[p.type] = p.value;
    return {
      date: `${parts.year}-${parts.month}-${parts.day}`,
      time: `${parts.hour}:${parts.minute}`,
    };
  }, [initialIso, detected, mountNow]);

  const [date, setDate] = useState(initial.date);
  const [time, setTime] = useState(initial.time);
  const [timezone, setTimezone] = useState(detected);

  const previewIso = useMemo(() => {
    if (!date || !time) return null;
    try {
      return zonedWallTimeToIso(date, time, timezone);
    } catch {
      return null;
    }
  }, [date, time, timezone]);

  const isFuture = previewIso ? new Date(previewIso).getTime() > mountNow : false;
  const canSubmit = Boolean(date && time && previewIso && isFuture && !isSaving);

  const preview = previewIso
    ? new Date(previewIso).toLocaleString([], {
        weekday: "short",
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
      })
    : "—";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#18222D]/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !isSaving) onClose();
      }}
    >
      <div className="w-full max-w-md rounded-[14px] border border-[#DCE6EC] bg-white shadow-lg">
        <div className="flex items-center justify-between border-b border-[#DCE6EC] px-5 py-3.5">
          <div className="flex items-center gap-2">
            <CalendarClock className="w-4 h-4 text-[#187CA4]" />
            <h3 className="text-[14px] font-semibold text-[#18222D]">{title}</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSaving}
            aria-label="Close"
            className="text-[#52606B] hover:text-[#18222D] rounded p-1 hover:bg-[#F8FBFC] disabled:opacity-50"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-5 py-4 space-y-4">
          <p className="text-[12.5px] text-[#52606B]">
            {postLabel} · publishing as{" "}
            <span className="font-medium text-[#18222D]">{accountName}</span>
          </p>

          {error && (
            <div
              role="alert"
              className="rounded-[8px] border border-[#F5C2C7] bg-[#FDF2F2] p-2.5 text-[12px] text-[#D9381E] flex items-start gap-2"
            >
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label htmlFor="sched-date" className="block text-[12px] font-semibold text-[#18222D]">
                Date
              </label>
              <input
                id="sched-date"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                disabled={isSaving}
                className="w-full rounded-[8px] border border-[#DCE6EC] bg-[#F8FBFC] px-3 py-2 text-[13px] text-[#18222D] focus:border-[#187CA4] focus:bg-white focus:outline-none focus:ring-1 focus:ring-[#187CA4] disabled:opacity-60"
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="sched-time" className="block text-[12px] font-semibold text-[#18222D]">
                Time
              </label>
              <input
                id="sched-time"
                type="time"
                value={time}
                onChange={(e) => setTime(e.target.value)}
                disabled={isSaving}
                className="w-full rounded-[8px] border border-[#DCE6EC] bg-[#F8FBFC] px-3 py-2 text-[13px] text-[#18222D] focus:border-[#187CA4] focus:bg-white focus:outline-none focus:ring-1 focus:ring-[#187CA4] disabled:opacity-60"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="sched-tz" className="block text-[12px] font-semibold text-[#18222D]">
              Timezone
            </label>
            <select
              id="sched-tz"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              disabled={isSaving}
              className="w-full rounded-[8px] border border-[#DCE6EC] bg-[#F8FBFC] px-3 py-2 text-[13px] text-[#18222D] focus:border-[#187CA4] focus:bg-white focus:outline-none focus:ring-1 focus:ring-[#187CA4] disabled:opacity-60"
            >
              {zones.map((z) => (
                <option key={z} value={z}>
                  {z.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </div>

          <div className="rounded-[8px] bg-[#EDF6F9] border border-[#DCE6EC] px-3 py-2.5">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-[#52606B]">
              Will publish
            </p>
            <p className="text-[13px] text-[#18222D] mt-0.5">
              {preview}{" "}
              <span className="text-[#52606B]">({timezone.replace(/_/g, " ")})</span>
            </p>
            {!isFuture && date && time && (
              <p className="text-[11.5px] text-[#D9381E] mt-1">
                Pick a time in the future.
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-[#DCE6EC] px-5 py-3.5">
          <button
            type="button"
            onClick={onClose}
            disabled={isSaving}
            className="rounded-[8px] border border-[#DCE6EC] bg-white px-4 py-2 text-[13px] font-medium text-[#52606B] hover:bg-[#F8FBFC] hover:text-[#18222D] disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => previewIso && onConfirm(previewIso, timezone)}
            disabled={!canSubmit}
            className="flex items-center gap-1.5 rounded-[8px] bg-[#187CA4] px-4 py-2 text-[13px] font-semibold text-white hover:bg-[#136384] disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
          >
            {isSaving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Saving…
              </>
            ) : (
              <>
                <CalendarClock className="w-4 h-4" /> {initialIso ? "Reschedule" : "Schedule"}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

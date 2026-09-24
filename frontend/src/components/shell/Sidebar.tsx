"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useBrand } from "@/context/BrandContext";
import {
  Building2,
  Megaphone,
  FileText,
  Calendar,
  Clapperboard,
  Users,
  Clock,
  Settings,
  ChevronsUpDown,
  Check,
  Plus,
  Pencil,
  type LucideIcon,
} from "lucide-react";

export type NavKey =
  | "home"
  | "campaigns"
  | "content"
  | "calendar"
  | "video"
  | "prospects"
  | "history";

interface NavItem {
  key: NavKey;
  label: string;
  icon: LucideIcon;
  href?: string; // omitted = not built yet (rendered but not navigable)
}

// Only items with a real destination get an href. Unbuilt destinations are
// rendered but disabled with a "Soon" marker, so the nav never links to a
// page that does not exist yet (they get wired as each screen is built).
const NAV: NavItem[] = [
  { key: "home", label: "Brand Profile", icon: Building2, href: "/brandsetup?mode=edit" },
  { key: "campaigns", label: "Campaigns", icon: Megaphone, href: "/campaigns" },
  { key: "content", label: "Content", icon: FileText },
  { key: "calendar", label: "Calendar", icon: Calendar, href: "/calendar" },
  { key: "video", label: "Video Studio", icon: Clapperboard, href: "/video-generation" },
  { key: "prospects", label: "Prospects", icon: Users, href: "/prospects" },
  { key: "history", label: "History", icon: Clock, href: "/history" },
];

interface Props {
  active: NavKey;
}

export default function Sidebar({ active }: Props) {
  const { user } = useAuth();
  const {
    brands,
    activeBrand,
    activeBrandId,
    setActiveBrandId,
    isLoading: loadingBrands,
  } = useBrand();
  const router = useRouter();
  const email = user?.email ?? "";

  const [open, setOpen] = useState(false);

  const switchTo = (id: string) => {
    setActiveBrandId(id);
    setOpen(false);
    if (typeof window !== "undefined" && window.location.pathname.startsWith("/campaigns/")) {
      router.push("/campaigns");
    }
  };

  return (
    <aside className="hidden md:flex w-[240px] shrink-0 flex-col border-r border-[#e6e9ec] bg-white h-screen sticky top-0">
      {/* Top Header: Logo + App Name linking to Landing Page */}
      <div className="px-4 py-3.5 border-b border-[#e6e9ec]">
        <Link
          href="/"
          className="flex items-center gap-2.5 group"
          title="Hipoclipse Landing Page"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.png" alt="Hipoclipse" className="w-7 h-7 rounded-lg object-contain" />
          <span className="text-[15px] font-bold tracking-tight text-[#1f2a30] group-hover:text-[#1174b8] transition-colors">
            Hipoclipse
          </span>
        </Link>
      </div>

      {/* Brand switcher */}
      <div className="p-3 relative">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-haspopup="menu"
          aria-expanded={open}
          className="w-full flex items-center gap-2 rounded-[10px] border border-[#e6e9ec] bg-[#f9fafb] hover:bg-[#f2f4f6] px-2.5 py-2 transition-colors text-left"
        >
          <span className="w-6 h-6 rounded-md bg-[#eef4f8] text-[#1174b8] grid place-items-center text-[11px] font-bold shrink-0">
            {(activeBrand?.company_name?.[0] || "B").toUpperCase()}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-[12.5px] font-semibold text-[#1f2a30] truncate">
              {loadingBrands ? "Loading…" : activeBrand?.company_name ?? "Set up your brand"}
            </span>
            <span className="block text-[10.5px] text-[#8a949c] truncate">
              {brands.length > 1 ? `${brands.length} brands` : "Active brand"}
            </span>
          </span>
          <ChevronsUpDown size={14} className="text-[#a6afb5] shrink-0" />
        </button>

        {open && (
          <>
            {/* click-outside backdrop */}
            <button
              type="button"
              aria-hidden="true"
              tabIndex={-1}
              onClick={() => setOpen(false)}
              className="fixed inset-0 z-40 cursor-default"
            />
            <div
              role="menu"
              className="absolute left-3 right-3 top-[calc(100%-4px)] z-50 rounded-[12px] border border-[#e6e9ec] bg-white shadow-lg p-1.5"
            >
              {brands.length > 0 && (
                <p className="px-2.5 pt-1 pb-1.5 text-[10px] font-semibold tracking-[0.12em] text-[#9aa4ac] uppercase">
                  Your brands
                </p>
              )}
              <div className="max-h-[240px] overflow-y-auto">
                {brands.map((b) => {
                  const isActive = b.id === activeBrandId;
                  return (
                    <button
                      key={b.id}
                      type="button"
                      role="menuitemradio"
                      aria-checked={isActive}
                      onClick={() => switchTo(b.id)}
                      className={`w-full flex items-center gap-2.5 rounded-[8px] px-2.5 py-2 text-[13px] text-left transition-colors ${
                        isActive
                          ? "bg-[#eaf3f5] text-[#116677] font-semibold"
                          : "text-[#3f4b53] hover:bg-[#f4f6f7]"
                      }`}
                    >
                      <span className="w-6 h-6 rounded-md bg-[#eef4f8] text-[#1174b8] grid place-items-center text-[11px] font-semibold shrink-0">
                        {(b.company_name[0] || "B").toUpperCase()}
                      </span>
                      <span className="flex-1 truncate">{b.company_name}</span>
                      {isActive && <Check size={15} className="shrink-0 text-[#116677]" />}
                    </button>
                  );
                })}
                {brands.length === 0 && !loadingBrands && (
                  <p className="px-2.5 py-2 text-[12.5px] text-[#8a949c]">No brands yet.</p>
                )}
              </div>

              <div className="border-t border-[#eef0f2] mt-1 pt-1">
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setOpen(false);
                    router.push("/brandsetup?mode=new");
                  }}
                  className="w-full flex items-center gap-2.5 rounded-[8px] px-2.5 py-2 text-[13px] text-[#3f4b53] hover:bg-[#f4f6f7] transition-colors"
                >
                  <Plus size={15} className="shrink-0 text-[#5a6771]" /> Add brand
                </button>
                {activeBrand && (
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setOpen(false);
                      router.push("/brandsetup?mode=edit");
                    }}
                    className="w-full flex items-center gap-2.5 rounded-[8px] px-2.5 py-2 text-[13px] text-[#3f4b53] hover:bg-[#f4f6f7] transition-colors"
                  >
                    <Pencil size={15} className="shrink-0 text-[#5a6771]" /> Edit current brand
                  </button>
                )}
              </div>
            </div>
          </>
        )}
      </div>

      <p className="px-5 pt-2 pb-1.5 text-[10px] font-semibold tracking-[0.12em] text-[#9aa4ac] uppercase">
        Workspace
      </p>

      {/* Nav */}
      <nav className="flex-1 px-2 space-y-0.5 overflow-y-auto" aria-label="Primary">
        {NAV.map((item) => {
          const Icon = item.icon;
          const isActive = item.key === active;
          const base =
            "w-full flex items-center gap-3 rounded-[9px] px-3 py-2 text-[14px] transition-colors";

          if (!item.href) {
            return (
              <span
                key={item.key}
                aria-disabled="true"
                title="Coming soon"
                className={`${base} text-[#b3bcc2] cursor-default select-none`}
              >
                <Icon size={17} className="shrink-0" />
                <span className="flex-1">{item.label}</span>
                <span className="text-[10px] font-medium text-[#c2cace] border border-[#e6e9ec] rounded px-1.5 py-0.5">
                  Soon
                </span>
              </span>
            );
          }

          return (
            <Link
              key={item.key}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={`${base} ${
                isActive
                  ? "bg-[#eaf3f5] text-[#116677] font-semibold"
                  : "text-[#5a6771] hover:bg-[#f4f6f7] hover:text-[#1f2a30]"
              }`}
            >
              <Icon size={17} className="shrink-0" />
              <span className="flex-1">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Bottom */}
      <div className="p-2 border-t border-[#eef0f2] space-y-0.5">
        <span
          aria-disabled="true"
          title="Coming soon"
          className="w-full flex items-center gap-3 rounded-[9px] px-3 py-2 text-[14px] text-[#b3bcc2] cursor-default select-none"
        >
          <Settings size={17} className="shrink-0" />
          <span className="flex-1">Settings</span>
          <span className="text-[10px] font-medium text-[#c2cace] border border-[#e6e9ec] rounded px-1.5 py-0.5">
            Soon
          </span>
        </span>

        <div className="flex items-center gap-2.5 rounded-[9px] px-3 py-2">
          <span className="w-8 h-8 rounded-full bg-[#12303a] text-white grid place-items-center text-xs font-semibold shrink-0">
            {user && email ? (email[0] || "U").toUpperCase() : "G"}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-[12.5px] font-medium text-[#1f2a30] truncate">
              {user && email ? email : "Guest"}
            </span>
            <span className="block text-[11px] text-[#8a949c] truncate">
              {user ? "Member" : "Not signed in"}
            </span>
          </span>
        </div>
      </div>
    </aside>
  );
}

"use client";

import Link from "next/link";
import {
  Plus,
  Home,
  Megaphone,
  Library,
  Sparkles,
  Settings,
  MessageSquare,
  PanelLeftClose,
  PanelLeft,
} from "lucide-react";

interface Props {
  isOpen: boolean;
  onToggle: () => void;
  onNewChat: () => void;
}

const recentChats = [
  "LinkedIn Campaign Strategy",
  "Q4 Product Launch",
  "WhatsApp Automation",
  "Enterprise Outreach",
];

export default function CampaignSidebar({
  isOpen,
  onToggle,
  onNewChat,
}: Props) {
  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={onToggle}
        title="Expand Sidebar"
        aria-label="Expand Sidebar"
        className="fixed top-20 left-4 z-40 p-2 rounded-lg bg-[#151D26] border border-white/[0.08] text-[#9AA6B2] hover:text-[#F5F7FA] hover:bg-[#1B2530] transition-colors shadow-sm hidden md:flex items-center justify-center cursor-pointer"
      >
        <PanelLeft size={17} />
      </button>
    );
  }

  return (
    <aside className="w-64 h-full bg-[#0E141B] border-r border-white/[0.08] flex flex-col justify-between flex-shrink-0 z-30 transition-all duration-200">
      {/* Top Header & New Campaign Action */}
      <div className="p-3.5 space-y-3">
        <div className="flex items-center justify-between px-2 py-1">
          <Link href="/" className="flex items-center space-x-2 group">
            <span className="text-lg font-bold tracking-tight text-[#F5F7FA] lowercase">
              hipoclipse <span className="text-[#20B8E5] text-xs font-semibold uppercase tracking-wider ml-1">AI</span>
            </span>
          </Link>

          <button
            type="button"
            onClick={onToggle}
            title="Collapse Sidebar"
            aria-label="Collapse Sidebar"
            className="p-1.5 rounded-md text-[#6B7785] hover:text-[#F5F7FA] hover:bg-white/[0.04] transition-colors cursor-pointer"
          >
            <PanelLeftClose size={16} />
          </button>
        </div>

        {/* Primary Action Button: + New Campaign */}
        <button
          type="button"
          onClick={onNewChat}
          className="w-full h-9 px-3 rounded-lg bg-[#20B8E5] hover:bg-[#1BA1CA] text-[#0E141B] font-semibold text-xs transition-colors flex items-center justify-center space-x-1.5 shadow-sm cursor-pointer"
        >
          <Plus size={15} strokeWidth={2.5} />
          <span>New Campaign</span>
        </button>

        {/* Core Workspace Navigation */}
        <nav className="space-y-0.5 pt-1">
          <Link
            href="/"
            className="flex items-center space-x-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-[#9AA6B2] hover:text-[#F5F7FA] hover:bg-white/[0.04] transition-colors"
          >
            <Home size={15} />
            <span>Home</span>
          </Link>
          <Link
            href="/dashboard"
            className="flex items-center space-x-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-[#9AA6B2] hover:text-[#F5F7FA] hover:bg-white/[0.04] transition-colors"
          >
            <Megaphone size={15} />
            <span>Campaigns</span>
          </Link>
          <Link
            href="/video-generation"
            className="flex items-center space-x-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-[#9AA6B2] hover:text-[#F5F7FA] hover:bg-white/[0.04] transition-colors"
          >
            <Library size={15} />
            <span>Content Library</span>
          </Link>
          <Link
            href="/brandsetup"
            className="flex items-center space-x-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-[#9AA6B2] hover:text-[#F5F7FA] hover:bg-white/[0.04] transition-colors"
          >
            <Sparkles size={15} />
            <span>Brand Voice</span>
          </Link>
        </nav>
      </div>

      {/* Middle: Recent Conversations List */}
      <div className="flex-1 overflow-y-auto px-3.5 py-2 space-y-1">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-[#6B7785] px-2.5 block mb-1.5">
          Recent Campaigns
        </span>
        {recentChats.map((chat, idx) => (
          <button
            key={chat}
            type="button"
            className={`w-full text-left flex items-center space-x-2 px-2.5 py-1.5 rounded-md text-xs transition-colors truncate cursor-pointer ${
              idx === 0
                ? "bg-white/[0.06] text-[#F5F7FA] font-medium"
                : "text-[#9AA6B2] hover:text-[#F5F7FA] hover:bg-white/[0.04]"
            }`}
          >
            <MessageSquare size={13} className="flex-shrink-0 text-[#6B7785]" />
            <span className="truncate">{chat}</span>
          </button>
        ))}
      </div>

      {/* Bottom: User Profile & Settings */}
      <div className="p-3 border-t border-white/[0.08] space-y-1.5">
        <Link
          href="/brandsetup"
          className="flex items-center space-x-2.5 px-2.5 py-1.5 rounded-md text-xs text-[#9AA6B2] hover:text-[#F5F7FA] hover:bg-white/[0.04] transition-colors"
        >
          <Settings size={15} />
          <span>Settings</span>
        </Link>

        <div className="flex items-center space-x-2.5 px-2 py-1.5 pt-2 border-t border-white/[0.04]">
          <div className="w-7 h-7 rounded-full bg-[#1B2530] border border-white/[0.1] text-[#F5F7FA] text-xs font-semibold flex items-center justify-center">
            OP
          </div>
          <div className="flex-1 min-w-0">
            <span className="text-xs font-medium text-[#F5F7FA] block truncate leading-tight">
              Operations Team
            </span>
            <span className="text-[11px] text-[#6B7785] block truncate">
              Enterprise Workspace
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}

"use client";

export default function BrandSetupHeader() {
  return (
    <div className="pb-6 border-b border-[#25303B]">
      {/* Small Muted Breadcrumb */}
      <div className="flex items-center space-x-2 text-xs text-[#6B7280] mb-2 font-medium">
        <span>Settings</span>
        <span>/</span>
        <span className="text-[#9CA3AF]">Brand Profile</span>
      </div>

      {/* Page Title: 28-32px semibold, no gradient text */}
      <h1 className="text-2xl sm:text-[28px] font-semibold text-[#F3F4F6] tracking-tight leading-tight">
        Brand Setup & Voice Signature
      </h1>

      {/* Short Readable Description */}
      <p className="text-xs sm:text-[13px] text-[#9CA3AF] mt-1 max-w-2xl leading-relaxed">
        Define your company&apos;s core profile, track record, and communication style to guide autonomous AI agents across all campaign and customer generations.
      </p>

      {/* Subtle Muted Informational Line */}
      <div className="mt-3 flex items-center space-x-2 text-xs text-[#6B7280]">
        <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />
        <span>1,536-dimensional vector embedding space synchronized</span>
      </div>
    </div>
  );
}

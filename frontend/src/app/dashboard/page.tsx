import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import DashboardHeader from "@/components/dashboard/DashboardHeader";
import DashboardKPIs from "@/components/dashboard/DashboardKPIs";
import GenerationTrendsChart from "@/components/dashboard/GenerationTrendsChart";
import SystemCapacityChart from "@/components/dashboard/SystemCapacityChart";
import RecentCampaignsTable from "@/components/dashboard/RecentCampaignsTable";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-[#0B0F14] text-[#F3F4F6] selection:bg-[#3B82F6]/30 selection:text-white flex flex-col font-sans">
      {/* Top Navigation */}
      <Navbar />

      {/* Main Content Container */}
      <main className="flex-1 pt-24 pb-12 px-4 sm:px-6 lg:px-8 max-w-[1440px] mx-auto w-full">
        {/* Section 1: Executive Dashboard Header & Controls */}
        <section className="mb-6">
          <DashboardHeader />
        </section>

        {/* Section 2: 4 Core Metric KPI Cards */}
        <section className="mb-6">
          <DashboardKPIs />
        </section>

        {/* Section 3: Dual Analytical Charts */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-6">
          {/* Graph 1: Generations & Engagement Trends */}
          <GenerationTrendsChart />

          {/* Graph 2: System Health & Infrastructure Capacity */}
          <SystemCapacityChart />
        </section>

        {/* Section 4: Recent Campaign Executions Table */}
        <section>
          <RecentCampaignsTable />
        </section>
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
}

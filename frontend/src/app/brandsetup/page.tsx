"use client";

import { useState, useEffect } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import BrandSetupHeader from "@/components/brandsetup/BrandSetupHeader";
import BrandProfileForm from "@/components/brandsetup/BrandProfileForm";
import { BrandProfileData } from "@/components/brandsetup/types";
import { companyApi } from "@/lib/api";

const initialFormData: BrandProfileData = {
  companyName: "Hipoclipse",
  industry: "Enterprise AI & Conversational MarTech",
  website: "https://hipoclipse.ai",
  targetAudience: "Global enterprise brands, B2B distributors, and retail conglomerates",
  description:
    "Hipoclipse builds intelligent sales platforms powered by autonomous conversational agents that empower global enterprises to digitize field sales, increase average order value, and drive 3X higher conversions directly on WhatsApp, mobile apps, and telephone.",
  trackRecord:
    "Digitized over 1 million retail tienditas across Latin America and Europe, automating over $4 Billion in transactions for Fortune 500 leaders including Coca-Cola FEMSA, Nestlé, and Mondelēz with a 24% conversion rate.",
  specializations: [
    "Conversational Commerce",
    "Autonomous Sales Agents",
    "Omnichannel AI Orchestration",
    "WhatsApp Automated Commerce",
    "Predictive SKU Recommendations",
  ],
  toneMessage:
    "We sound like an experienced, trusted enterprise advisor who is warm, direct, and pragmatic. We communicate like a tech founder talking to a retail store owner over coffee—always helpful, data-grounded, and solutions-oriented. We never use aggressive sales spam, high-pressure urgency, or robotic corporate jargon.",
  sampleMessage:
    "Hello Roberto! Hope your store had a great weekend. Based on your weekly sales velocity, you're on pace to run out of 2.5L Coca-Cola by Thursday. I have a 1-tap replenishment pre-calculated with your 5% volume rebate. Would you like me to reserve the delivery for tomorrow morning?",
  selectedTraits: [
    "Authoritative",
    "Empathetic",
    "Innovative",
    "Data-Driven",
    "Pragmatic",
  ],
  negativeGuardrails: [
    "Never use aggressive high-pressure sales spam",
    "Never make unsubstantiated revenue guarantees",
    "Avoid robotic, corporate generic jargon",
  ],
};

export default function BrandSetupPage() {
  const [formData, setFormData] = useState<BrandProfileData>(initialFormData);
  const [isSaved, setIsSaved] = useState(false);
  const [companyId, setCompanyId] = useState<string | null>(null);

  useEffect(() => {
    async function loadBrand() {
      try {
        const list = await companyApi.list();
        if (list && list.length > 0) {
          const profile = await companyApi.get(list[0].id);
          if (profile) {
            setCompanyId(profile.id);
            // Parse brand_guidelines if JSON, or use fields
            try {
              const parsed = JSON.parse(profile.brand_guidelines);
              setFormData((prev) => ({ ...prev, ...parsed, companyName: profile.company_name || prev.companyName }));
            } catch {
              setFormData((prev) => ({
                ...prev,
                companyName: profile.company_name || prev.companyName,
                toneMessage: profile.brand_tone || prev.toneMessage,
              }));
            }
          }
        }
      } catch (err) {
        console.warn("Could not load backend company profile, using default:", err);
      }
    }
    loadBrand();
  }, []);

  const handleSave = async () => {
    setIsSaved(true);
    try {
      const payload = {
        company_name: formData.companyName || "Hipoclipse",
        brand_guidelines: JSON.stringify(formData),
        brand_tone: formData.toneMessage || "Authoritative, warm, and pragmatic",
      };
      if (companyId) {
        await companyApi.update(companyId, payload);
      } else {
        const created = await companyApi.create(payload);
        if (created && created.id) setCompanyId(created.id);
      }
    } catch (err) {
      console.error("Failed to persist brand profile:", err);
    }
    setTimeout(() => {
      setIsSaved(false);
    }, 4000);
  };

  return (
    <div className="min-h-screen bg-[#0B1117] text-[#F3F4F6] selection:bg-[#3B82F6]/30 selection:text-white flex flex-col font-sans">
      {/* Top Navbar */}
      <Navbar />

      {/* Main Enterprise Form Container */}
      <main className="flex-1 pt-24 pb-16 px-4 sm:px-6">
        <div className="max-w-[920px] mx-auto w-full">
          {/* Header */}
          <div className="mb-8">
            <BrandSetupHeader />
          </div>

          {/* Form */}
          <BrandProfileForm
            formData={formData}
            setFormData={setFormData}
            onSave={handleSave}
            isSaved={isSaved}
          />
        </div>
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
}

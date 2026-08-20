'use client';

import { useState, useEffect, useRef } from 'react';
import Button from '@/components/ui/Button';
import styles from './page.module.css';
import { companyApi, CompanyProfile, ApiError } from '@/lib/api';

export default function BrandSetup() {
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [companyName, setCompanyName] = useState('');
  const [brandDescription, setBrandDescription] = useState('');
  const [brandTone, setBrandTone] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saved' | 'error'>('idle');
  const [loading, setLoading] = useState(true);
  const [uploadingImages, setUploadingImages] = useState(false);
  const [galleryImages, setGalleryImages] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load existing profile on mount
  useEffect(() => {
    const loadProfile = async () => {
      try {
        const profiles = await companyApi.list();
        if (profiles && profiles.length > 0) {
          const isDummy = (str?: string) => !str || /dupco|test|mock|ad4b23bb|techify/i.test(str);
          // Find first clean profile or fallback to first profile
          const p = profiles.find((prof) => !isDummy(prof.company_name)) || profiles[0];
          setProfile(p);

          const rawName = p.company_name || '';
          setCompanyName(isDummy(rawName) ? '' : rawName);

          const rawGuidelines = p.brand_guidelines || '';
          setBrandDescription(isDummy(rawGuidelines) ? '' : rawGuidelines);

          const rawTone = p.brand_tone || '';
          setBrandTone(isDummy(rawTone) ? '' : rawTone);

          setGalleryImages(p.reference_image_urls || []);
        }
      } catch {
        // No profile yet, form stays empty
      } finally {
        setLoading(false);
      }
    };
    loadProfile();
  }, []);

  const handleSave = async () => {
    if (!companyName.trim()) return;
    setSaving(true);
    setSaveStatus('idle');
    try {
      let saved: CompanyProfile;
      if (profile) {
        saved = await companyApi.update(profile.id, {
          company_name: companyName,
          brand_guidelines: brandDescription,
          brand_tone: brandTone || undefined,
        });
      } else {
        saved = await companyApi.create({
          company_name: companyName,
          brand_guidelines: brandDescription,
          brand_tone: brandTone || undefined,
        });
      }
      setProfile(saved);
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch (err) {
      setSaveStatus('error');
      console.error('Save failed:', err instanceof ApiError ? err.message : err);
    } finally {
      setSaving(false);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (!files.length || !profile) return;
    setUploadingImages(true);
    try {
      const result = await companyApi.uploadImages(profile.id, files);
      const updated = await companyApi.get(profile.id);
      setGalleryImages(updated.reference_image_urls || []);
      if (result.failed?.length) {
        console.warn('Some uploads failed:', result.failed);
      }
    } catch (err) {
      console.error('Image upload failed:', err);
    } finally {
      setUploadingImages(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleRemoveImage = async (index: number) => {
    if (!profile) return;
    try {
      await companyApi.removeImage(profile.id, index);
      setGalleryImages((prev) => prev.filter((_, i) => i !== index));
    } catch (err) {
      console.error('Remove image failed:', err);
    }
  };

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.loadingSpinner} />
        <p className={styles.loadingText}>Synchronizing Brand Memory...</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Page Header */}
      <div className={styles.header}>
        <div>
          <div className={styles.headerBadge}>
            <span className={styles.pulseDot} />
            BRAND IDENTITY MEMORY
          </div>
          <h1 className={styles.title}>Brand Identity Setup</h1>
          <p className={styles.subtitle}>
            Configure your company profile, voice guidelines, and visual reference assets for AI neural training.
          </p>
        </div>
      </div>

      {/* 2-Column Responsive Grid */}
      <div className={styles.grid}>
        
        {/* ── Left Column: Company Profile Form ── */}
        <div className={styles.leftCard}>
          <div className={styles.cardHeader}>
            <div className={styles.iconContainer}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
            </div>
            <div>
              <h2 className={styles.cardTitle}>Company Profile</h2>
              <p className={styles.cardSubtitle}>Core identity & brand tone parameters</p>
            </div>
          </div>

          <div className={styles.formGroup}>
            <div className={styles.labelRow}>
              <label className={styles.label}>COMPANY NAME</label>
              <span className={styles.requiredTag}>REQUIRED</span>
            </div>
            <input
              type="text"
              className={styles.input}
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Enter your company name..."
            />
          </div>

          <div className={styles.formGroup}>
            <div className={styles.labelRow}>
              <label className={styles.label}>BRAND DESCRIPTION & GUIDELINES</label>
              <span className={styles.helperText}>{brandDescription.length} / 1000</span>
            </div>
            <textarea
              className={styles.textarea}
              value={brandDescription}
              onChange={(e) => setBrandDescription(e.target.value)}
              placeholder="Describe your brand values, target audience, key selling points, and core message..."
              maxLength={1000}
            />
          </div>

          <div className={styles.formGroupStretch}>
            <div className={styles.labelRow}>
              <label className={styles.label}>BRAND TONE & VOICE SIGNATURE</label>
              <span className={styles.helperText}>{brandTone.length} / 500</span>
            </div>
            <textarea
              className={styles.textarea}
              value={brandTone}
              onChange={(e) => setBrandTone(e.target.value)}
              placeholder="Describe your tone of voice (e.g. Professional, authoritative, bold, friendly, witty...)"
              maxLength={500}
            />
          </div>

          <div className={styles.actionRow}>
            <Button
              variant={saveStatus === 'error' ? 'danger' : 'primary'}
              onClick={handleSave}
              disabled={saving || !companyName.trim()}
              className={styles.saveButton}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
              {saving ? 'SAVING PROFILE...' : saveStatus === 'saved' ? '✓ PROFILE SAVED' : saveStatus === 'error' ? 'ERROR — RETRY' : 'SAVE BRAND PROFILE'}
            </Button>

            {saveStatus === 'saved' && (
              <span className={styles.saveSuccessText}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                Memory Synchronized!
              </span>
            )}
          </div>
        </div>

        {/* ── Right Column: Logo & Imagery Assets ── */}
        <div className={styles.rightColumn}>
          <div className={styles.rightCard}>
            <div className={styles.cardHeader}>
              <div className={styles.iconContainer}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
              </div>
              <div>
                <h2 className={styles.cardTitle}>Logo &amp; Visual Memory</h2>
                <p className={styles.cardSubtitle}>Reference logos &amp; lifestyle graphics</p>
              </div>
            </div>

            {/* Upload Box */}
            <div
              className={`${styles.uploadBox} ${!profile ? styles.uploadDisabled : ''}`}
              onClick={() => profile && fileInputRef.current?.click()}
            >
              <div className={styles.uploadIcon}>
                {uploadingImages ? (
                  <svg className={styles.spinnerIcon} width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
                ) : (
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/></svg>
                )}
              </div>
              <p className={styles.uploadTitle}>
                {uploadingImages ? 'Uploading Assets...' : !profile ? 'Save Profile First to Enable Upload' : 'Drop brand assets here or click to upload'}
              </p>

              {/* Format Badges */}
              <div className={styles.badgeRow}>
                <span className={styles.formatBadge}>JPG</span>
                <span className={styles.formatBadge}>PNG</span>
                <span className={styles.formatBadge}>WEBP</span>
                <span className={styles.limitBadge}>MAX 5MB</span>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                multiple
                style={{ display: 'none' }}
                onChange={handleFileChange}
              />
            </div>

            {/* Gallery Section */}
            <div className={styles.gallery}>
              <div className={styles.galleryHeader}>
                <h3 className={styles.galleryTitle}>REFERENCE GALLERY</h3>
                <span className={styles.galleryCount}>{galleryImages.length} ASSETS</span>
              </div>

              <div className={styles.galleryGrid}>
                {galleryImages.length === 0 ? (
                  <>
                    <div className={styles.emptyGallerySlot}>
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                      <span>Slot 1 Empty</span>
                    </div>
                    <div className={styles.emptyGallerySlot}>
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                      <span>Slot 2 Empty</span>
                    </div>
                  </>
                ) : (
                  galleryImages.map((url, i) => (
                    <div key={i} className={styles.galleryItem}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={url} alt={`Brand asset ${i + 1}`} className={styles.assetImg} />
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemoveImage(i);
                        }}
                        className={styles.removeBtn}
                        title="Remove asset"
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Info Banner */}
          <div className={styles.infoBox}>
            <div className={styles.infoIcon}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
            </div>
            <p>
              Providing high-resolution logos and lifestyle imagery allows the{' '}
              <strong>Aether Neural Engine</strong> to synthesize perfectly matched visual campaign assets.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}

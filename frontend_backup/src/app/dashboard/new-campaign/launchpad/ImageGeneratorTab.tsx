'use client';

import React, { useState, useRef, useEffect } from 'react';
import Button from '@/components/ui/Button';

interface BrandSnapshot {
  brand_name: string;
  industry: string;
  tone_of_voice: string;
  personality_descriptors: string[];
  color_palette: string[];
  style_guidance: string;
}

interface ImageGenerationState {
  base_idea: string;
  brand_snapshot: BrandSnapshot;
  brand_visual_translation: string;
  brand_adjustments: string;
  refinements: string[];
  current_final_prompt: string;
  iteration_count: number;
}

interface ImageGeneratorTabProps {
  campaignId: string;
}

export default function ImageGeneratorTab({ campaignId }: ImageGeneratorTabProps) {
  const [state, setState] = useState<ImageGenerationState | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [baseIdea, setBaseIdea] = useState('');
  const [instruction, setInstruction] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [finalAssetUrl, setFinalAssetUrl] = useState<string | null>(null);
  const [finalCaption, setFinalCaption] = useState<string | null>(null);
  const [isFinalizing, setIsFinalizing] = useState(false);

  const startSession = async () => {
    if (!baseIdea.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/campaigns/${campaignId}/image-session/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_idea: baseIdea })
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || 'Failed to start session');
      }
      const data = await res.json();
      setState(data.state);
      setImageUrl(data.image_url);
    } catch (err: any) {
      setError(err.message || 'Image generation failed, try again');
    } finally {
      setIsLoading(false);
    }
  };

  const refineSession = async () => {
    if (!state || !instruction.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/campaigns/${campaignId}/image-session/refine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state, instruction })
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || 'Failed to refine image');
      }
      const data = await res.json();
      setState(data.state);
      setImageUrl(data.image_url);
      setInstruction('');
    } catch (err: any) {
      setError(err.message || 'Image generation failed, try again');
    } finally {
      setIsLoading(false);
    }
  };

  const finalizeSession = async () => {
    if (!state || !imageUrl) return;
    setIsFinalizing(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/campaigns/${campaignId}/image-session/finalize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state, image_url: imageUrl })
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || 'Failed to finalize image');
      }
      const data = await res.json();
      setFinalAssetUrl(data.permanent_image_url);
      setFinalCaption(data.caption);
    } catch (err: any) {
      setError(err.message || 'Failed to lock and finalize image');
    } finally {
      setIsFinalizing(false);
    }
  };

  if (finalAssetUrl) {
    return (
      <div style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.5rem', alignItems: 'center' }}>
        <div style={{ textAlign: 'center', color: '#10b981', fontWeight: 600 }}>✅ Image locked and saved to Supabase!</div>
        <img src={finalAssetUrl} alt="Finalized Asset" style={{ maxWidth: '500px', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
        <div style={{ background: '#f3f4f6', padding: '1.5rem', borderRadius: '8px', width: '100%', maxWidth: '600px', color: '#1f2937' }}>
          <strong>Generated Caption:</strong>
          <p style={{ marginTop: '0.5rem', whiteSpace: 'pre-wrap' }}>{finalCaption}</p>
        </div>
        {/* Autopilot deferred for future phase */}
        <Button disabled style={{ opacity: 0.5 }}>🚀 AUTOPILOT TO LINKEDIN (Coming Soon)</Button>
      </div>
    );
  }

  return (
    <div style={{ padding: '2rem 0', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ background: 'rgba(59, 130, 246, 0.1)', color: '#3b82f6', padding: '0.75rem 1rem', borderRadius: '6px', fontSize: '0.875rem' }}>
        ℹ️ Brand colors and tone are applied; logo/reference images aren't used by this generator yet.
      </div>
      
      {error && <div style={{ color: '#ef4444', background: 'rgba(239, 68, 68, 0.1)', padding: '0.75rem', borderRadius: '6px' }}>{error}</div>}

      {!state ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '600px' }}>
          <h3 style={{ margin: 0, color: '#1f2937' }}>Describe your image idea</h3>
          <textarea
            value={baseIdea}
            onChange={(e) => setBaseIdea(e.target.value)}
            placeholder="E.g., A futuristic laptop on a sleek desk..."
            style={{ width: '100%', padding: '1rem', borderRadius: '8px', border: '1px solid #d1d5db', minHeight: '100px', resize: 'vertical' }}
            disabled={isLoading}
          />
          <Button onClick={startSession} disabled={isLoading}>
            {isLoading ? 'Starting...' : 'Start Generation'}
          </Button>
        </div>
      ) : (
        <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
          {/* Image Display */}
          <div style={{ flex: '1 1 400px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
            {isLoading ? (
              <div style={{ width: '100%', aspectRatio: '1/1', background: '#e5e7eb', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' }}>
                <span style={{ color: '#9ca3af' }}>Generating...</span>
              </div>
            ) : (
              imageUrl && <img src={imageUrl} alt="Generated Iteration" style={{ width: '100%', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
            )}
            
            <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>Iteration: {state.iteration_count} / 25</div>
            
            {state.iteration_count >= 8 && state.iteration_count < 25 && (
              <div style={{ color: '#d97706', fontSize: '0.875rem', textAlign: 'center' }}>
                You've been refining this for a while — want to keep going, or lock in your current version?
              </div>
            )}
            {state.iteration_count >= 25 && (
              <div style={{ color: '#ef4444', fontSize: '0.875rem', textAlign: 'center' }}>
                Maximum iterations reached for this session. Please lock in the final version.
              </div>
            )}
          </div>

          {/* Refinement Interface */}
          <div style={{ flex: '1 1 300px', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <h4 style={{ margin: 0, color: '#1f2937' }}>Refine Image</h4>
              <p style={{ margin: 0, fontSize: '0.875rem', color: '#6b7280' }}>Instruct the AI to change specific details.</p>
            </div>
            
            <textarea
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder="E.g., Make the lighting more dramatic, remove the background elements..."
              style={{ width: '100%', padding: '1rem', borderRadius: '8px', border: '1px solid #d1d5db', minHeight: '100px', resize: 'vertical' }}
              disabled={isLoading || isFinalizing || state.iteration_count >= 25}
            />
            
            <div style={{ display: 'flex', gap: '1rem' }}>
              <Button 
                onClick={refineSession} 
                disabled={!instruction.trim() || isFinalizing || state.iteration_count >= 25 || isLoading}
                style={{ flex: 1 }}
              >
                {isLoading ? 'Refining...' : 'Refine'}
              </Button>
              <Button 
                onClick={finalizeSession} 
                disabled={isLoading || isFinalizing}
                variant="secondary"
                style={{ flex: 1, background: '#10b981', color: 'white', border: 'none' }}
              >
                {isFinalizing ? 'Locking...' : 'Lock & Generate Caption'}
              </Button>
            </div>
            
            {/* Context Insights */}
            <div style={{ marginTop: '1rem', padding: '1rem', background: '#f9fafb', borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '0.75rem', color: '#4b5563' }}>
              <strong style={{ display: 'block', marginBottom: '0.5rem' }}>Active Brand Translation:</strong>
              {state.brand_visual_translation}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

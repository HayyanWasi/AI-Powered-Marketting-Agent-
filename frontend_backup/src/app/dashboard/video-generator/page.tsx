'use client';

import { useEffect, useState } from 'react';
import Button from '@/components/ui/Button';
import { campaignApi, Campaign, videoApi } from '@/lib/api';
import styles from './VideoGenerator.module.css';

export default function VideoGeneratorPage() {
  const [prompt, setPrompt] = useState<string>('');
  const [generating, setGenerating] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [autopilotLive, setAutopilotLive] = useState(false);
  const [showModal, setShowModal] = useState(false);


  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setError('Please enter a campaign prompt first.');
      return;
    }
    setGenerating(true);
    setError('');
    setVideoUrl(null);
    setAutopilotLive(false);

    try {
      const res = await videoApi.generate('standalone', prompt.trim());
      setVideoUrl(res.video_url);
      setShowModal(true);
    } catch (err: any) {
      setError(err.message || 'Failed to generate video.');
    } finally {
      setGenerating(false);
    }
  };

  const handleAutopilot = () => {
    setAutopilotLive(true);
    setTimeout(() => {
      alert('Autopilot configuration activated for LinkedIn!');
    }, 500);
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.badge}>VIDEO GENERATOR</div>
        <h1 className={styles.title}>AI Director & Renderer</h1>
        <p className={styles.subtitle}>
          Generate highly interactive short-form videos for your campaigns automatically.
        </p>
      </header>

      <main className={styles.main}>
          <div className={styles.panel}>
            <div className={styles.selectorGroup}>
              <label className={styles.label}>Campaign Context / Prompt</label>
              <textarea 
                className={styles.textarea}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                disabled={generating}
                placeholder="e.g., I want to host an agentic AI seminar for students and industry professionals at Zaitoon Ashraf IT Park..."
                rows={5}
              />
            </div>

            {error && <div className={styles.error}>{error}</div>}

            {!videoUrl && !generating && (
              <div className={styles.emptyState}>
                <p>Enter a campaign context to write script, render visuals, and composite audio.</p>
                <Button 
                  variant="primary" 
                  onClick={handleGenerate} 
                  disabled={!prompt.trim()}
                  style={{ background: '#55E6C1', color: '#000', fontWeight: 'bold' }}
                >
                  🎬 GENERATE VIDEO
                </Button>
              </div>
            )}

            {generating && (
              <div className={styles.generatingState}>
                <div className={styles.pulseIcon}>🤖</div>
                <div className={styles.genTitle}>AI Director is building your video...</div>
                <p className={styles.genText}>This process will take several minutes to generate and render 60fps video.</p>
              </div>
            )}

            {videoUrl && !generating && (
              <div className={styles.successState}>
                <div className={styles.successIcon}>✨</div>
                <div className={styles.genTitle}>Video Generated Successfully!</div>
                <Button 
                  variant="primary" 
                  onClick={() => setShowModal(true)} 
                  style={{ background: '#55E6C1', color: '#000', fontWeight: 'bold', marginTop: '1rem' }}
                >
                  ▶️ WATCH VIDEO
                </Button>
              </div>
            )}
          </div>
      </main>

      {showModal && videoUrl && (
        <div className={styles.modalOverlay} onClick={() => setShowModal(false)}>
          <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <button className={styles.closeButton} onClick={() => setShowModal(false)}>✕</button>
            <h2 className={styles.modalTitle}>Your Campaign Video</h2>
            
            <div className={styles.videoWrapper}>
              <video src={videoUrl} controls autoPlay className={styles.videoPlayer} />
            </div>
            
            <div className={styles.actionRow}>
              <Button 
                variant="primary" 
                onClick={handleGenerate} 
                disabled={generating}
                style={{ background: '#374151', color: '#fff' }}
              >
                🔄 REGENERATE
              </Button>
              <Button 
                variant="primary" 
                onClick={handleAutopilot}
                disabled={autopilotLive}
                style={{ background: autopilotLive ? '#3b82f6' : '#0a66c2', color: '#fff', fontWeight: 'bold' }}
              >
                {autopilotLive ? '✓ LIVE ON LINKEDIN' : '🚀 POST TO LINKEDIN'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

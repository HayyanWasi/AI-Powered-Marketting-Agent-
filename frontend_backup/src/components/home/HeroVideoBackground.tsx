'use client';

import React from 'react';
import styles from './HeroVideoBackground.module.css';

export default function HeroVideoBackground() {
  return (
    <div className={styles.videoContainer}>
      {/* HTML5 Video Element sourcing /4k-video-bg.mp4 */}
      <video
        src="/4k-video-bg.mp4"
        autoPlay
        loop
        muted
        playsInline
        className={styles.videoElement}
      />

      {/* Light Slate Overlay Sheen for 100% Crisp Typography Legibility */}
      <div className={styles.overlaySheen} />
      <div className={styles.radialGlowSheen} />
    </div>
  );
}

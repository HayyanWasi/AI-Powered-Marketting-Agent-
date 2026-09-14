'use client';

import React, { useState, useEffect, useRef } from 'react';
import dynamic from 'next/dynamic';
import styles from './Hero3DCanvas.module.css';

// Dynamically import Spline to prevent SSR hydration buffer errors
const Spline = dynamic(() => import('@splinetool/react-spline'), {
  ssr: false,
});

interface Particle {
  x: number;
  y: number;
  z: number;
  baseX: number;
  baseY: number;
  baseZ: number;
  vx: number;
  vy: number;
  vz: number;
}

export default function Hero3DCanvas() {
  const [useSpline] = useState(false);
  const [splineError, setSplineError] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Canvas 3D Interactive Particle & Neural Mesh System
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = canvas.parentElement?.clientWidth || 500);
    let height = (canvas.height = canvas.parentElement?.clientHeight || 450);

    const particles: Particle[] = [];
    const numParticles = 45;

    for (let i = 0; i < numParticles; i++) {
      const x = (Math.random() - 0.5) * 300;
      const y = (Math.random() - 0.5) * 300;
      const z = (Math.random() - 0.5) * 300;
      particles.push({
        x,
        y,
        z,
        baseX: x,
        baseY: y,
        baseZ: z,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        vz: (Math.random() - 0.5) * 0.4,
      });
    }

    let mouseX = 0;
    let mouseY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouseX = ((e.clientX - rect.left) / width - 0.5) * 2;
      mouseY = ((e.clientY - rect.top) / height - 0.5) * 2;
    };

    window.addEventListener('mousemove', handleMouseMove);

    const handleResize = () => {
      if (!canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.clientWidth;
      height = canvas.height = canvas.parentElement.clientHeight;
    };

    window.addEventListener('resize', handleResize);

    let angleX = 0;
    let angleY = 0;

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      angleY += 0.003 + mouseX * 0.005;
      angleX += 0.002 + mouseY * 0.005;

      const cosX = Math.cos(angleX);
      const sinX = Math.sin(angleX);
      const cosY = Math.cos(angleY);
      const sinY = Math.sin(angleY);

      const projectedPoints: { x: number; y: number; scale: number }[] = [];

      // Render 3D Neural Nodes
      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        p.z += p.vz;

        if (Math.abs(p.x - p.baseX) > 40) p.vx *= -1;
        if (Math.abs(p.y - p.baseY) > 40) p.vy *= -1;
        if (Math.abs(p.z - p.baseZ) > 40) p.vz *= -1;

        // Rotate Y
        const x1 = p.x * cosY - p.z * sinY;
        const z1 = p.z * cosY + p.x * sinY;

        // Rotate X
        const y1 = p.y * cosX - z1 * sinX;
        const z2 = z1 * cosX + p.y * sinX;

        // Perspective Projection
        const perspective = 400;
        const scale = perspective / (perspective + z2 + 200);
        const projX = width / 2 + x1 * scale;
        const projY = height / 2 + y1 * scale;

        projectedPoints.push({ x: projX, y: projY, scale });

        // Draw particle dot
        ctx.beginPath();
        ctx.arc(projX, projY, Math.max(1.5, 3.5 * scale), 0, Math.PI * 2);
        ctx.fillStyle = scale > 0.8 ? '#55E6C1' : '#0D9488';
        ctx.shadowColor = '#33D9B2';
        ctx.shadowBlur = 12 * scale;
        ctx.fill();
      });

      // Draw Neural Network Connection Lines
      for (let i = 0; i < projectedPoints.length; i++) {
        for (let j = i + 1; j < projectedPoints.length; j++) {
          const p1 = projectedPoints[i];
          const p2 = projectedPoints[j];
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 90) {
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            const alpha = (1 - dist / 90) * 0.35;
            ctx.strokeStyle = `rgba(85, 230, 193, ${alpha})`;
            ctx.lineWidth = 1;
            ctx.stroke();
          }
        }
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <div className={styles.canvasWrapper}>
      {/* Brand Color Ambient Glow (#33D9B2 / #55E6C1) */}
      <div className={styles.brandGlow} />

      {useSpline && !splineError ? (
        <div className={styles.splineContainer}>
          <Spline
            scene="https://prod.spline.design/6Wnt13Kinauh260y/scene.splinecode"
            onError={() => setSplineError(true)}
            className={styles.splineCanvas}
          />
        </div>
      ) : (
        /* High-Performance 3D Interactive Neural Canvas */
        <div className={styles.neuralCanvasCard}>
          <canvas ref={canvasRef} className={styles.interactiveCanvas} />

          {/* Floating Glassmorphism Status Badge */}
          <div className={styles.overlayBadge}>
            <div className={styles.pulseDot} />
            <span>NEURAL 3D CLUSTER • REALTIME AI ENGINE</span>
          </div>
        </div>
      )}
    </div>
  );
}

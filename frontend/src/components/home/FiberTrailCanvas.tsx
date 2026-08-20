'use client';

import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import styles from './FiberTrailCanvas.module.css';

export default function FiberTrailCanvas() {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. Scene, Camera, Renderer Setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color('#F8FAFC');

    const width = window.innerWidth;
    const height = window.innerHeight;

    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
    camera.position.set(0, 0, 100);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // 2. Helper to Create Dynamic Canvas Pulse Textures
    function createPulseTexture(pulseColorHex: string) {
      const canvas = document.createElement('canvas');
      canvas.width = 512;
      canvas.height = 32;
      const ctx = canvas.getContext('2d');

      if (ctx) {
        ctx.clearRect(0, 0, 512, 32);
        // Base transparent background
        const grad = ctx.createLinearGradient(0, 0, 512, 0);
        grad.addColorStop(0, 'rgba(0,0,0,0)');
        grad.addColorStop(0.3, 'rgba(0,0,0,0)');
        grad.addColorStop(0.7, pulseColorHex);
        grad.addColorStop(0.85, '#FFFFFF'); // Glowing White head
        grad.addColorStop(1, 'rgba(0,0,0,0)');

        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, 512, 32);
      }

      const texture = new THREE.CanvasTexture(canvas);
      texture.wrapS = THREE.RepeatWrapping;
      texture.wrapT = THREE.ClampToEdgeWrapping;
      texture.repeat.set(4, 1);
      return texture;
    }

    const neonColors = [
      '#33D9B2', // Primary Mint
      '#0EA5E9', // Light Cyan
      '#FFFFFF', // Soft White
      '#55E6C1', // Light Mint
    ];

    // 3. Create 3D Fiber Cables & Overlay Traveling Pulse Meshes
    const numCables = 8;
    const pulseTextures: THREE.CanvasTexture[] = [];
    const geometriesToDispose: THREE.BufferGeometry[] = [];
    const materialsToDispose: THREE.Material[] = [];
    const pulseMeshes: { mesh: THREE.Mesh; texture: THREE.CanvasTexture; speed: number }[] = [];

    for (let i = 0; i < numCables; i++) {
      const points: THREE.Vector3[] = [];
      const numPoints = 14;
      const radiusOffset = 25 + Math.random() * 35;
      const angleOffset = (i / numCables) * Math.PI * 2;

      for (let j = 0; j < numPoints; j++) {
        const z = -j * 80 + 100;
        const angle = angleOffset + j * 0.45;
        const x = Math.cos(angle) * (radiusOffset + Math.sin(j * 0.5) * 16);
        const y = Math.sin(angle) * (radiusOffset + Math.cos(j * 0.5) * 16);
        points.push(new THREE.Vector3(x, y, z));
      }

      const curve = new THREE.CatmullRomCurve3(points, false, 'centripetal', 0.5);

      // A. Base Wire Cable Mesh (Thin Cool Slate #334155, Opacity 0.25)
      const baseRadius = 1.2;
      const baseGeometry = new THREE.TubeGeometry(curve, 120, baseRadius, 10, false);
      geometriesToDispose.push(baseGeometry);

      const baseMaterial = new THREE.MeshBasicMaterial({
        color: 0x334155,
        transparent: true,
        opacity: 0.25,
        depthWrite: false,
      });
      materialsToDispose.push(baseMaterial);

      const baseMesh = new THREE.Mesh(baseGeometry, baseMaterial);
      scene.add(baseMesh);

      // B. Overlay Traveling Neon Pulse Tube Mesh
      const pulseRadius = baseRadius + 0.3;
      const pulseGeometry = new THREE.TubeGeometry(curve, 120, pulseRadius, 10, false);
      geometriesToDispose.push(pulseGeometry);

      const pulseColor = neonColors[i % neonColors.length];
      const pulseTexture = createPulseTexture(pulseColor);
      pulseTextures.push(pulseTexture);

      const pulseMaterial = new THREE.MeshBasicMaterial({
        map: pulseTexture,
        transparent: true,
        opacity: 0.85,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      materialsToDispose.push(pulseMaterial);

      const pulseMesh = new THREE.Mesh(pulseGeometry, pulseMaterial);
      scene.add(pulseMesh);

      const speed = 0.012 + Math.random() * 0.006;
      pulseMeshes.push({ mesh: pulseMesh, texture: pulseTexture, speed });
    }

    // 4. Scroll Velocity Acceleration
    let scrollSpeedBonus = 0;
    let lastScrollY = window.scrollY;
    let scrollTimeout: NodeJS.Timeout;

    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      const delta = Math.abs(currentScrollY - lastScrollY);
      scrollSpeedBonus = Math.min(0.04, delta * 0.001);
      lastScrollY = currentScrollY;

      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        scrollSpeedBonus = 0;
      }, 150);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });

    // 5. Window Resize Handler
    const handleResize = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);

    // 6. Animation Loop (Traveling Pulses Stream continuously along cables)
    let animationFrameId: number;
    let time = 0;

    const animate = () => {
      time += 0.005;

      // Animate Camera Position & Perspective Depth
      camera.position.x = Math.sin(time * 0.8) * 10;
      camera.position.y = Math.cos(time * 0.6) * 10;
      camera.lookAt(0, 0, -200);

      // Translate Texture Offsets so Neon Light Pulses stream endlessly forward along the wires
      pulseMeshes.forEach((item) => {
        item.texture.offset.x -= item.speed + scrollSpeedBonus;
      });

      renderer.render(scene, camera);
      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    // 7. Cleanup & Memory Safety
    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', handleResize);
      clearTimeout(scrollTimeout);

      pulseTextures.forEach((t) => t.dispose());
      geometriesToDispose.forEach((g) => g.dispose());
      materialsToDispose.forEach((m) => m.dispose());
      renderer.dispose();

      if (container && renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  return <div ref={containerRef} className={styles.canvasContainer} />;
}

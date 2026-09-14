# Hipoclipse Design System & UI Specification (`DESIGN.md`)

> **Comprehensive Design Specification for Hipoclipse Landing Page**  
> Extracted and synthesized directly from the production implementation, DOM inspect element metrics, CSS variable tokens, and Webflow motion choreography.

---

## 1. Brand Identity & Design Philosophy

### 1.1 Brand Concept
**Hipoclipse** is an enterprise conversational AI and autonomous marketing agent platform. The design conveys enterprise trust, cutting-edge machine learning power, and human accessibility.

### 1.2 Core Visual Tension: Sand & Obsidian
Rather than choosing between a strictly light or strictly dark aesthetic, the interface creates high-contrast visual rhythm by layering **floating obsidian cards** (`#0E151C`) with generous corner radii (`24px`) over an **organic warm sand canvas** (`#FAF8F4`):
* **Sand Canvas (`#FAF8F4`)**: Grounds daytime reading, editorial stories, platform overview diagrams, and social proof.
* **Obsidian Cards (`#0E151C`)**: Encapsulates high-tech product modules (Hero, Sales Agents, Video Showcases, Security, and CTA) with deep ambient glows and dot-grid textures.

### 1.3 Signature Accent Gradient
The brand is anchored by an electric three-stop linear gradient that represents transformation, intelligence, and vitality:
```css
/* Hipoclipse Brand Gradient */
background: linear-gradient(90deg, #00C2EE 0%, #D75DFF 50%, #EDAE3E 100%);
```
* **Electric Cyan (`#00C2EE`)**: Technology, connectivity, precision.
* **Vibrant Violet (`#D75DFF`)**: Artificial intelligence, synthesis, innovation.
* **Warm Amber (`#EDAE3E`)**: Business growth, conversions, human warmth.

---

## 2. Layout & Viewport Specifications

| Property | Exact Metric | Implementation Rule |
| :--- | :--- | :--- |
| **Canvas Max Width** | `1520.8px` | `max-w-[1520.8px] mx-auto` |
| **Side Gutters (Desktop)** | `45.6125px` (`3vw`) | `padding: 0px clamp(16px, 3vw, 45.6125px)` |
| **Floating Card Radius** | `24px` | `rounded-[24px]` on all major dark section cards |
| **Inner Card Radius** | `16px` | `rounded-2xl` on sub-cards, testimonials, and tabs |
| **Interactive Element Radius**| `8px` | `rounded-[8px]` on primary action buttons and inputs |
| **Pill Badges** | `9999px` | `rounded-full` for category chips and feature tags |
| **Header Height** | `80px` | `h-[80px]` floating navbar anchored at top |

---

## 3. Design Tokens Architecture

### 3.1 Color Tokens

```css
:root {
  /* Primitive Colors */
  --sand-50: #FAF8F4;
  --sand-100: #F4EFE6;
  --charcoal-900: #0E151C;
  --charcoal-800: #141B24;
  --charcoal-700: #1C2633;
  --charcoal-border: #272F38;
  --charcoal-border-hover: #363B42;

  /* Accent Spectrum */
  --accent-cyan: #00C2EE;
  --accent-purple: #D75DFF;
  --accent-amber: #EDAE3E;
  --accent-green: #25D366;

  /* Semantic Token Mapping */
  --bg-page: var(--sand-50);
  --text-primary: var(--charcoal-900);
  --text-muted: rgba(14, 21, 28, 0.75);

  --bg-dark-card: var(--charcoal-900);
  --bg-dark-surface: var(--charcoal-800);
  --text-dark-primary: #FAF8F4;
  --text-dark-muted: rgba(250, 248, 244, 0.8);
  --border-dark-card: var(--charcoal-border);
  --border-dark-hover: var(--charcoal-border-hover);
}
```

### 3.2 Typography System

* **Primary Typeface**: [Plus Jakarta Sans](https://fonts.google.com/specimen/Plus+Jakarta+Sans)
* **Fallback Stack**: `system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
* **Base Metrics**: Size `17.065px`, Line-height `1.5` (`25.5975px`), Weight `400`.

#### Type Scale Table

| Role | Font Size | Line Height | Weight | Letter Spacing | CSS Equivalent |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Hero Title** | `3.75rem` (`60px`) | `1.12` | 800 (ExtraBold) | `-0.025em` | `text-4xl sm:text-6xl font-extrabold tracking-tight` |
| **Section Title (H2)** | `3rem` (`48px`) | `1.15` | 800 (ExtraBold) | `-0.02em` | `text-3xl sm:text-5xl font-extrabold tracking-tight` |
| **Card Metric Stat** | `3.75rem` (`60px`) | `1.0` | 900 (Black) | `-0.03em` | `text-5xl sm:text-6xl font-black tracking-tight` |
| **Subheading (H3)** | `1.5rem` (`24px`) | `1.3` | 700 (Bold) | `-0.015em` | `text-xl sm:text-2xl font-bold` |
| **Lead Subtitle** | `1.125rem` (`18px`)| `1.6` | 400 (Regular) | `normal` | `text-base sm:text-lg leading-relaxed` |
| **Body Default** | `1.066rem` (`17.065px`)| `1.5` | 400 (Regular) | `normal` | `text-[17.065px] leading-normal` |
| **Button / Nav Links** | `0.9375rem` (`15px`)| `1.0` | 500 / 600 | `normal` | `text-[15px] font-medium` |
| **Pill Badges** | `0.75rem` (`12px`) | `1.0` | 600 (SemiBold) | `+0.05em` | `text-xs font-semibold tracking-wider uppercase` |

---

## 4. Motion & Micro-Interactions

### 4.1 Webflow-Inspired Scroll Reveal (`[data-reveal]`)
All primary viewport elements start displaced vertically with zero opacity and smoothly settle into position upon crossing the 15% viewport intersection threshold.

```css
/* Base scroll-reveal state */
[data-reveal] {
  opacity: 0;
  transform: translate3d(0, 22px, 0);
  transition: opacity 0.7s cubic-bezier(0.16, 1, 0.3, 1),
              transform 0.7s cubic-bezier(0.16, 1, 0.3, 1);
  will-change: opacity, transform;
}

/* Triggered state */
[data-reveal].is-revealed {
  opacity: 1;
  transform: translate3d(0, 0, 0);
}
```

#### Staggered Delay Orchestration
```html
<div data-reveal data-reveal-delay="50">Pill Badge</div>
<h1 data-reveal data-reveal-delay="150">Main Heading</h1>
<p data-reveal data-reveal-delay="250">Description</p>
<div data-reveal data-reveal-delay="350">Action CTA</div>
```

### 4.2 Signature Dual-Text Sliding Button (`.yalo-btn` / `.hipoclipse-btn`)
Buttons feature two stacked identical text nodes inside an overflow-hidden slot. On hover, the visible line slides upward by `-100%` while the second line replaces it seamlessly. Simultaneously, a vibrant gradient backdrop rises from `110%` to `0%`.

```css
.yalo-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.yalo-btn-text-wrapper {
  display: inline-flex;
  flex-direction: column;
  height: 1.25em;
  overflow: hidden;
  position: relative;
  z-index: 2;
}

.yalo-btn-text {
  display: block;
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.yalo-btn:hover .yalo-btn-text {
  transform: translateY(-100%);
}

.yalo-btn-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, #00c2ee 0%, #d75dff 50%, #edae3e 100%);
  transform: translateY(110%);
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  z-index: 1;
}

.yalo-btn:hover .yalo-btn-bg {
  transform: translateY(0%);
}
```

---

## 5. Component Specifications

### 5.1 Floating Navigation Bar
* **Container**: `fixed top-0 left-0 right-0 z-50 pt-2.5`
* **Nav Shell**: `max-w-[1429.57px] mx-auto h-[80px] rounded-[16px] px-6 lg:px-[45.6px] bg-[#0E151C] border border-[#272F38]/60`
* **Logo**: `hipoclipse` text wordmark, `text-[26px] font-black tracking-tight text-white lowercase`
* **Links**:
  * `Platform` (`/platform`)
  * `Dashboard` (`/dashboard`)
  * `Brandsetup` (`/brandsetup`)
  * `New Campaign` (`/new-campaign`)
  * `Video Generation` (`/video-generation`)
  * `History` (`/history`)
* **Action Buttons**:
  1. **Get Started**: `bg-[#FAF8F4] text-[#0E151C] rounded-[8px] h-[40px] px-4 font-medium`
  2. **Contact Us**: `bg-[#0E151C] text-[#FAF8F4] border border-[#45484D] rounded-[8px] h-[40px] px-4 font-medium`
  3. **EN Switcher**: `bg-white text-black font-bold text-[14px] rounded-[8px] h-[40px] px-3.5`

### 5.2 Hero Section
* **Card**: Dark card `rounded-[24px] bg-[#0E151C]` with subtle dot grid pattern:
  ```css
  background-image: radial-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px);
  background-size: 24px 24px;
  ```
* **Backdrop Glow**: Radial gradient `blur-[130px] from-[#00c2ee]/15 via-[#d75dff]/20 to-[#edae3e]/15`.
* **Headline**: `"The first "` + `<span className="text-gradient">intelligent sales platform with agents.</span>`
* **Right Media**: Lottie vector animation (`/lottie/hero.json`) with circular portrait badges.

### 5.3 Brand Logo Marquee Ticker
* **Container**: Dark card `rounded-[24px] bg-[#0E151C] py-8`
* **Animation**: CSS continuous linear translate:
  ```css
  @keyframes ticker {
    0% { transform: translateX(0); }
    100% { transform: translateX(-50%); }
  }
  ```
* **Logos**: Coca-Cola FEMSA, Nestlé, Mondelēz, ICICI Bank, Sears, Aeroméxico, Coppel (monochrome white with 70% opacity, 100% on hover).

### 5.4 Platform Overview
* **Background**: Pure Sand `#FAF8F4`.
* **Badge**: Pill chip `bg-[#0e151c]/5 text-[#0e151c]` with sparkle icon.
* **Heading**: `<span className="text-gradient">Everything</span> your customers need, <span className="text-gradient">in one place</span>`
* **Journey Diagram Graphic**: White container card `rounded-2xl p-4 shadow-2xl border border-[#0e151c]/10`.

### 5.5 Sales Agent Metrics Section
* **Card**: Dark card `rounded-[24px] bg-[#0E151C] py-20`
* **Headline**: `"We recreate with AI"` `<br />` `<span className="text-gradient">the best seller</span>`
* **3x Metric Cards**: `bg-[#141B24]/90 border border-[#272F38] rounded-2xl p-8 hover:-translate-y-1.5 transition-all`
  * `3X`: Conversion than a traditional e-commerce site
  * `+40%`: Average ticket
  * `+49%`: In SKUs per order

### 5.6 Customer Voices & Global Impact
* **Background**: Sand `#FAF8F4`.
* **Quote Slider**: Centered glassmorphic card with circular gradient avatar, italic quote, customer name in `#00c2ee`, and pagination dots (`active: w-6 bg-[#d75dff]`).
* **5-Column Stats Grid**:
  * `+4 B`: In transactions
  * `+40`: Country presence
  * `+4.4 M`: Active stores
  * `+12%`: Increase in sales
  * `Millions`: USD in loans placed

### 5.7 Video Case Studies Section
* **Card**: Dark card `rounded-[24px] bg-[#0E151C]`
* **Tabs**: Coca-Cola FEMSA, Nestlé, Mondelēz, Yupi with active bottom gradient bar.
* **Media**: 16:9 poster thumbnail with frosted-glass play button opening an embedded YouTube lightbox modal.

### 5.8 SPARK Matrix & Security Section
* **SPARK Matrix**: Dark card containing leader badge graphic with dual-column value narrative.
* **Security & Governance**: Lottie architecture animation (`/lottie/security.json`) demonstrating SOC2, ISO 27001, and enterprise data privacy protection.

### 5.9 Omnichannel CTA & Footer
* **CTA Banner**: Dark container with subtle texture overlay (`/images/cta-bg.webp`) and prominent "Discover How →" primary button.
* **Footer**:
  * Lowercase `hipoclipse` logo
  * Navigation links: Platform, Dashboard, Brandsetup, New Campaign, Video Generation, History
  * Single-input corporate email newsletter subscription form
  * Copyright notice and social media SVG icons (YouTube, LinkedIn, X, Facebook)

---

## 6. Accessibility & Responsiveness Guidelines

1. **Color Contrast**:
   * Sand background `#FAF8F4` paired with `#0E151C` provides a contrast ratio of `16.4:1` (exceeds WCAG AAA).
   * Dark cards `#0E151C` paired with `#FAF8F4` provides a contrast ratio of `16.4:1`.
2. **Reduced Motion**:
   * In `globals.css`, `@media (prefers-reduced-motion: reduce)` automatically sets `[data-reveal]` to `opacity: 1` and `transform: none` with zero duration.
3. **Responsive Breakpoints**:
   * `< 640px` (Mobile): Single-column stacks, mobile hamburger drawer, touch-friendly `44px` targets.
   * `640px - 1024px` (Tablet): 2-column grids for metrics and stats.
   * `> 1024px` (Desktop): Full multi-column grids, floating fixed navbar, horizontal brand tab layouts.

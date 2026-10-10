"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { Navbar } from "../components/Navbar";
import {
  ArrowDown,
  Camera,
  Satellite,
  FileCheck,
  Shield,
  Fingerprint,
  ChevronRight,
} from "lucide-react";

/* ── NDVI Counter Animation (Direct DOM update - 0 React re-renders) ───── */
function NdviCounter({ target = 0.718, duration = 2000 }: { target?: number; duration?: number }) {
  const spanRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = spanRef.current;
    if (!el) return;

    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (prefersReducedMotion) {
      el.textContent = target.toFixed(3);
      return;
    }

    const start = performance.now();
    let raf: number;
    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      if (el) {
        el.textContent = (eased * target).toFixed(3);
      }
      if (progress < 1) {
        raf = requestAnimationFrame(animate);
      }
    };
    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  return (
    <span ref={spanRef} className="tabular-nums font-heading font-bold text-canopy">
      0.000
    </span>
  );
}

/* ── Hardware-Accelerated Hero Video (Auto-pauses offscreen) ──────────── */
function HeroVideo() {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          video.play().catch(() => {});
        } else {
          video.pause();
        }
      },
      { threshold: 0.15 }
    );

    observer.observe(video);
    return () => observer.disconnect();
  }, []);

  return (
    <div className="xl:pl-2">
      <div className="rounded-[30px] bg-surface p-3 shadow-[0_10px_24px_rgba(31,27,23,0.05)] border border-strata/80 transform-gpu">
        <div className="overflow-hidden rounded-[24px] border border-strata-mid bg-[#e6c96d] shadow-[0_8px_20px_rgba(31,27,23,0.08)] transform-gpu">
          <video
            ref={videoRef}
            src="/videos/neerdrishti-demo.mp4"
            muted
            autoPlay
            loop
            playsInline
            preload="metadata"
            className="block w-full h-[300px] sm:h-[360px] xl:h-[420px] object-cover object-[center_36%] transform-gpu will-change-transform"
          />
        </div>
      </div>
    </div>
  );
}

/* ── MAIN PAGE ──────────────────────────────────────────────── */
export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      {/* ═══════════════════════════════════════════════════════
          HERO — Split: copy left, data visualization right
          ═══════════════════════════════════════════════════════ */}
      <header className="relative bg-surface border-b border-strata">
        <div className="w-full px-3 sm:px-4 lg:px-5 py-16 sm:py-20 lg:py-24">
          <div className="grid grid-cols-1 xl:grid-cols-[0.92fr_1.08fr] gap-8 xl:gap-10 items-center">
            {/* Left side: heading + intro + CTA + field note */}
            <div className="flex flex-col">
              <h1 className="text-[28px] sm:text-[36px] lg:text-[42px] xl:text-[48px] font-bold tracking-[-0.05em] leading-[1.02] text-basalt max-w-[520px]">
                Smart Watershed
                <span className="block">Monitoring</span>
              </h1>

              <p className="mt-5 text-[15px] sm:text-[16px] text-basalt-light leading-relaxed max-w-[480px]">
                NeerDrishti compares field and satellite data to verify the lasting, measurable,
                and credible impact of watershed works.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link
                  href="/dashboard"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-reservoir hover:bg-reservoir-light text-white text-[14px] font-semibold transition-colors"
                >
                  Open Dashboard
                </Link>

                <a
                  href="#how-it-works"
                  className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg text-[14px] font-medium text-basalt-light hover:text-basalt border border-strata-mid hover:border-strata-deep transition-colors"
                >
                  <span>How it works</span>
                  <ArrowDown className="w-3.5 h-3.5" />
                </a>
              </div>

              <div className="mt-4 bg-surface border border-strata-mid rounded-[20px] p-4 sm:p-5 shadow-[0_10px_30px_rgba(31,27,23,0.06)] max-w-[500px]">
                <div className="flex items-center justify-between border-b border-strata pb-3 mb-4">
                  <div>
                    <p className="text-[10px] uppercase tracking-[0.14em] text-basalt-light/60">Field note</p>
                    <h3 className="mt-1 text-[22px] text-basalt">Kotharwadi</h3>
                  </div>
                  <div className="rounded-full bg-reservoir-faint px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-reservoir">
                    Verified
                  </div>
                </div>

                <div className="space-y-3 text-[13px] text-basalt-light">
                  <div className="flex items-center justify-between border-b border-strata pb-2">
                    <span>Site status</span>
                    <span className="font-semibold text-basalt">Confirmed</span>
                  </div>
                  <div className="flex items-center justify-between border-b border-strata pb-2">
                    <span>NDVI</span>
                    <span className="font-semibold text-canopy tabular-nums"><NdviCounter target={0.718} /></span>
                  </div>
                  <div className="flex items-center justify-between border-b border-strata pb-2">
                    <span>NDWI</span>
                    <span className="font-semibold text-sentinel tabular-nums">0.142</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Coordinates</span>
                    <span className="font-semibold text-basalt tabular-nums">19.085°N, 74.750°E</span>
                  </div>
                </div>

                <div className="mt-5 rounded-[16px] bg-strata px-4 py-3 text-[12px] text-basalt-light leading-relaxed">
                  <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.12em] text-basalt-light/60 mb-2">
                    <span>Inspection</span>
                    <span>March 2026</span>
                  </div>
                  <p className="m-0">“Vegetation is holding well and runoff appears contained. Photo evidence aligns with satellite readings; no major anomaly noted.”</p>
                </div>
              </div>
            </div>

            {/* Right side — hardware-accelerated video */}
            <HeroVideo />
          </div>
        </div>
      </header>

      {/* ═══════════════════════════════════════════════════════
          HOW IT WORKS — Keep only the essentials
          ═══════════════════════════════════════════════════════ */}
      <section id="how-it-works" className="border-b border-strata">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-20">
          <div className="border-l-[3px] border-sentinel pl-4 mb-10">
            <h2 className="text-[28px] sm:text-[34px] lg:text-[40px] font-semibold text-basalt">
              How verification works
            </h2>
            <p className="mt-1.5 text-[16px] sm:text-[18px] text-basalt-light max-w-2xl">
              One site. One photo. One check against the satellite record.
            </p>
          </div>

          {/* Pipeline — horizontal on desktop, vertical on mobile */}
          <div className="flex flex-col lg:flex-row lg:items-stretch gap-0">
            {/* Step 1 */}
            <div className="flex-1 flex flex-col lg:flex-row items-start lg:items-center gap-4 p-6 sm:p-8 bg-surface rounded-lg lg:rounded-r-none border border-strata-mid lg:border-r-0">
              <div className="w-12 h-12 rounded-md bg-reservoir-faint flex items-center justify-center shrink-0">
                <Camera className="w-5 h-5 text-reservoir" />
              </div>
              <div>
                  <h3 className="text-[17px] sm:text-[18px] font-semibold text-basalt">Capture the site</h3>
                <p className="text-[14px] sm:text-[15px] text-basalt-light mt-0.5 leading-relaxed">
                  Upload a photo from the field. The system records the location and checks the
                  metadata before the observation is used for review.
                </p>              </div>
            </div>

            {/* Connector */}
            <div className="hidden lg:flex items-center px-0">
              <div className="w-8 h-[2px] bg-strata-mid" />
              <ChevronRight className="w-4 h-4 text-strata-deep -mx-1" />
            </div>
            <div className="lg:hidden flex justify-center py-1">
              <div className="w-[2px] h-6 bg-strata-mid" />
            </div>

            {/* Step 2 */}
            <div className="flex-1 flex flex-col lg:flex-row items-start lg:items-center gap-4 p-6 sm:p-8 bg-surface border border-strata-mid lg:border-x-0 rounded-lg lg:rounded-none">
              <div className="w-12 h-12 rounded-md bg-sentinel-faint flex items-center justify-center shrink-0">
                <Satellite className="w-5 h-5 text-sentinel" />
              </div>
              <div>
                <h3 className="text-[17px] sm:text-[18px] font-semibold text-basalt">Check the land remotely</h3>
                <p className="text-[14px] sm:text-[15px] text-basalt-light mt-0.5 leading-relaxed">
                  Sentinel-2 data is pulled for that exact point to compare vegetation, water,
                  and seasonal change against what the field photo suggests.
                </p>
              </div>
            </div>

            {/* Connector */}
            <div className="hidden lg:flex items-center px-0">
              <div className="w-8 h-[2px] bg-strata-mid" />
              <ChevronRight className="w-4 h-4 text-strata-deep -mx-1" />
            </div>
            <div className="lg:hidden flex justify-center py-1">
              <div className="w-[2px] h-6 bg-strata-mid" />
            </div>

            {/* Step 3 */}
            <div className="flex-1 flex flex-col lg:flex-row items-start lg:items-center gap-4 p-6 sm:p-8 bg-surface rounded-lg lg:rounded-l-none border border-strata-mid lg:border-l-0">
              <div className="w-12 h-12 rounded-md bg-canopy-faint flex items-center justify-center shrink-0">
                <FileCheck className="w-5 h-5 text-canopy" />
              </div>
              <div>
                <h3 className="text-[17px] sm:text-[18px] font-semibold text-basalt">Prepare the record</h3>
                <p className="text-[14px] sm:text-[15px] text-basalt-light mt-0.5 leading-relaxed">
                  The final record pulls together the photo, health indicators, and any anomaly
                  notes in a clean report that can be shared with the team or audited later.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════
          FOOTER
          ═══════════════════════════════════════════════════════ */}
      <footer className="bg-surface border-t border-strata">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-[12px] text-basalt-light/70">
          <div className="flex items-center gap-2">
           <div className="w-6 h-6 rounded bg-reservoir flex items-center justify-center text-white text-[9px] font-bold">
             नी
           </div>
           <span className="font-medium text-basalt">@2026 NeerDrishti</span>
          </div>

          <div className="flex items-center gap-5">
           <Link href="/" className="hover:text-basalt transition-colors">Home</Link>
           <Link href="/dashboard" className="hover:text-basalt transition-colors">Dashboard</Link>
          </div>
        </div>
      </footer>

    </div>
  );
}

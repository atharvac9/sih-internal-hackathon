"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, Compass } from "lucide-react";

interface NavbarProps {
  onScanClick?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onScanClick }) => {
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register" | null>(null);

  const isDashboard = pathname.startsWith("/dashboard") || pathname.startsWith("/observatory");
  const isHome = pathname === "/";
  const isTeam = pathname.startsWith("/team");

  useEffect(() => {
    let ticking = false;
    let lastScrolled = window.scrollY > 80;
    const onScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          const nextScrolled = window.scrollY > 80;
          if (nextScrolled !== lastScrolled) {
            setScrolled(nextScrolled);
            lastScrolled = nextScrolled;
          }
          ticking = false;
        });
        ticking = true;
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Lock body scroll when mobile menu is open
  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [mobileOpen]);

  const navLinks = isDashboard
    ? [
        { href: "/dashboard", label: "Dashboard", active: isDashboard },
        { href: "/team", label: "Team", active: isTeam },
        { href: "/", label: "Home", active: isHome },
      ]
    : [
        { href: "/", label: "Home", active: isHome },
        { href: "/dashboard", label: "Dashboard", active: isDashboard },
        { href: "/team", label: "Team", active: isTeam },
      ];

  return (
    <>
      <header
        className={`no-print sticky top-0 z-50 transition-all duration-300 ease-out ${
          scrolled
            ? "h-12 bg-[#1d352f]/95 backdrop-blur-md border-b border-white/10 shadow-[0_8px_18px_rgba(0,0,0,0.22)]"
            : "h-16 bg-[#1d352f] border-b border-white/10"
        }`}
      >
        <div className="w-full px-3 sm:px-4 lg:px-5 h-full flex items-center justify-between gap-4">
          {/* Brand */}
          <Link href="/" className="flex items-center shrink-0 group ml-0">
            <div className="rounded-[30px] bg-[#183a35]/70 p-[2px] shadow-[0_8px_20px_rgba(11,25,22,0.22)] ring-1 ring-white/10 transition-all duration-300">
              <img
                src="/logo-clean.png"
                alt="NeerDrishti logo"
                className={`block object-contain transition-all duration-300 rounded-[28px] ${
                  scrolled ? "h-9 sm:h-10" : "h-12 sm:h-14"
                }`}
              />
            </div>
          </Link>

          {/* Desktop Nav Links */}
          <nav className="hidden md:flex flex-1 items-center justify-center gap-2">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`relative rounded-lg px-4 py-2 text-[13px] font-medium transition-all duration-200 ease-out ${
                  link.active
                    ? "bg-[#e7f1ec] text-[#1d352f] shadow-[0_0_0_1px_rgba(255,255,255,0.2)]"
                    : "text-white/80 hover:text-white hover:bg-white/10 hover:shadow-[inset_0_0_0_1px_rgba(255,255,255,0.12)]"
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          {/* Right: login/register + Mobile toggle */}
          <div className="flex items-center gap-3 ml-auto">
            <div className="hidden sm:flex items-center gap-2 relative justify-end">
              <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-2 py-1.5">
                <button
                  type="button"
                  onClick={() => setAuthMode((prev) => (prev === "login" ? null : "login"))}
                  className="rounded-md bg-[#e7f1ec] px-2.5 py-1.5 text-[11px] font-semibold text-[#1d352f] hover:bg-white transition-colors"
                >
                  Login
                </button>
                <button
                  type="button"
                  onClick={() => setAuthMode((prev) => (prev === "register" ? null : "register"))}
                  className="rounded-md border border-white/15 bg-transparent px-2.5 py-1.5 text-[11px] font-semibold text-white hover:bg-white/10 transition-colors"
                >
                  Register
                </button>
              </div>

              {authMode && (
                <div className="absolute right-0 top-[calc(100%+10px)] w-64 rounded-xl border border-white/10 bg-[#1d352f] p-3 shadow-[0_12px_28px_rgba(0,0,0,0.2)] z-20">
                  <label className="block mb-1 text-[10px] uppercase tracking-[0.14em] text-white/60">
                    {authMode === "login" ? "Login with email" : "Register with email"}
                  </label>
                  <input
                    type="email"
                    placeholder="you@example.com"
                    aria-label="Email"
                    className="w-full rounded-md border border-white/10 bg-white/5 px-2.5 py-2 text-[12px] text-white placeholder:text-white/50 focus:outline-none"
                  />
                </div>
              )}
            </div>

            {/* Mobile hamburger */}
            <button
              onClick={() => setMobileOpen(true)}
              className="md:hidden flex items-center justify-center w-9 h-9 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
              aria-label="Open menu"
            >
              <Menu className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* ── Mobile Full-Screen Menu ──────────────────────────────── */}
      {mobileOpen && (
        <div className="fixed inset-0 z-[100] md:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-basalt/40 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />

          {/* Panel — slides from right */}
          <div className="absolute right-0 top-0 bottom-0 w-[min(320px,85vw)] bg-[#1d352f] text-white shadow-2xl flex flex-col animate-in slide-in-from-right duration-200">
            {/* Close button */}
            <div className="flex items-center justify-between px-5 h-16 border-b border-strata">
              <span className="font-heading font-semibold text-basalt">Menu</span>
              <button
                onClick={() => setMobileOpen(false)}
                className="w-9 h-9 flex items-center justify-center rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
                aria-label="Close menu"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Links */}
            <nav className="flex-1 px-4 py-6 flex flex-col gap-1">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  className={`flex items-center px-4 py-3 rounded-lg text-[15px] font-medium transition-all duration-200 ${
                    link.active
                      ? "bg-[#e7f1ec] text-[#1d352f] font-semibold shadow-[inset_0_0_0_1px_rgba(255,255,255,0.15)]"
                      : "text-white/80 hover:text-white hover:bg-white/10 hover:shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]"
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </nav>

            {/* Bottom actions */}
            <div className="px-4 pb-6 pt-2 border-t border-white/10 space-y-2">
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setAuthMode((prev) => (prev === "login" ? null : "login"))}
                  className="flex-1 rounded-lg bg-[#e7f1ec] px-3 py-2.5 text-[13px] font-semibold text-[#1d352f] hover:bg-white transition-colors"
                >
                  Login
                </button>
                <button
                  type="button"
                  onClick={() => setAuthMode((prev) => (prev === "register" ? null : "register"))}
                  className="flex-1 rounded-lg border border-white/15 bg-transparent px-3 py-2.5 text-[13px] font-semibold text-white hover:bg-white/10 transition-colors"
                >
                  Register
                </button>
              </div>
              {authMode && (
                <div className="rounded-lg border border-white/10 bg-white/5 p-2">
                  <label className="mb-1 block text-[10px] uppercase tracking-[0.14em] text-white/60">
                    {authMode === "login" ? "Login with email" : "Register with email"}
                  </label>
                  <input
                    type="email"
                    placeholder="you@example.com"
                    aria-label="Email"
                    className="w-full bg-transparent text-[13px] text-white placeholder:text-white/50 focus:outline-none"
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

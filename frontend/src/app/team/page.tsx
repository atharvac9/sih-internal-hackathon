"use client";

import React from "react";
import Link from "next/link";
import { Navbar } from "../../components/Navbar";
import {
  Users,
  Compass,
  ShieldCheck,
  Droplets,
  ArrowRight,
  Globe2,
  UserPlus,
  Tag,
} from "lucide-react";

interface TeamMemberSlot {
  id: number;
  slotNumber: string;
  name: string;
  role: string;
  area: string;
  bio: string;
  skills: string[];
}

// 6 empty slots for teammates to fill in their details
const teamSlots: TeamMemberSlot[] = [
  {
    id: 1,
    slotNumber: "Slot 01",
    name: "",
    role: "",
    area: "",
    bio: "",
    skills: [],
  },
  {
    id: 2,
    slotNumber: "Slot 02",
    name: "",
    role: "",
    area: "",
    bio: "",
    skills: [],
  },
  {
    id: 3,
    slotNumber: "Slot 03",
    name: "",
    role: "",
    area: "",
    bio: "",
    skills: [],
  },
  {
    id: 4,
    slotNumber: "Slot 04",
    name: "",
    role: "",
    area: "",
    bio: "",
    skills: [],
  },
  {
    id: 5,
    slotNumber: "Slot 05",
    name: "",
    role: "",
    area: "",
    bio: "",
    skills: [],
  },
  {
    id: 6,
    slotNumber: "Slot 06",
    name: "",
    role: "",
    area: "",
    bio: "",
    skills: [],
  },
];

export default function TeamPage() {
  return (
    <div className="min-h-screen bg-[#f5f0e6] text-basalt flex flex-col selection:bg-reservoir/20 selection:text-reservoir font-body">
      {/* Top Navigation */}
      <Navbar />

      {/* Hero Header */}
      <section className="bg-[#f7f3ee] border-b border-strata-mid py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center flex flex-col items-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-reservoir-faint border border-reservoir/20 text-reservoir text-xs font-semibold mb-4">
            <Users className="w-3.5 h-3.5 text-reservoir" />
            <span>Multidisciplinary Engineering & Science Team</span>
          </div>

          <h1 className="font-heading text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-basalt">
            Core Project Contributors & Researchers
          </h1>

          <p className="mt-4 text-base sm:text-lg text-basalt-light max-w-2xl leading-relaxed">
            NeerDrishti brings together hydrologists, geospatial engineers, and machine learning researchers dedicated to open, verifiable watershed telemetry.
          </p>

          <div className="mt-8 flex items-center gap-3">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-reservoir hover:bg-reservoir-light text-white font-medium text-sm transition-all shadow-[0_8px_20px_rgba(47,90,79,0.18)]"
            >
              <Compass className="w-4 h-4" />
              <span>Launch Dashboard</span>
            </Link>
            <Link
              href="/"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-surface hover:bg-strata border border-strata-mid text-basalt font-medium text-sm transition-all"
            >
              <span>Back to Home</span>
            </Link>
          </div>
        </div>
      </section>

      {/* Team Slots Section */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-14 flex flex-col gap-14">
        <div>
          <div className="text-center max-w-2xl mx-auto mb-10">
            <div className="inline-block px-2.5 py-0.5 rounded-full bg-strata-light border border-strata-dark text-[11px] font-semibold text-basalt-muted uppercase tracking-wider mb-2">
              Team Roster • 6 Positions
            </div>
            <h2 className="font-heading text-2xl font-bold tracking-tight text-basalt">
              Team Members & Roles
            </h2>
            <p className="text-sm text-basalt-muted mt-2">
              Teammates can fill in their names, roles, focus areas, and domains below.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {teamSlots.map((slot) => {
              const hasName = Boolean(slot.name && slot.name.trim().length > 0);
              const hasRole = Boolean(slot.role && slot.role.trim().length > 0);
              const hasArea = Boolean(slot.area && slot.area.trim().length > 0);
              const hasBio = Boolean(slot.bio && slot.bio.trim().length > 0);
              const hasSkills = Boolean(slot.skills && slot.skills.length > 0);

              const initials = hasName
                ? slot.name
                    .split(" ")
                    .map((n) => n[0])
                    .join("")
                    .slice(0, 2)
                    .toUpperCase()
                : null;

              return (
                <div
                  key={slot.id}
                  className={`bg-surface rounded-xl border ${
                    hasName
                      ? "border-strata-mid"
                      : "border-dashed border-strata-deep/60 hover:border-reservoir/50"
                  } p-6 shadow-[0_8px_24px_rgba(31,27,23,0.04)] transition-all flex flex-col justify-between gap-5 relative group`}
                >
                  {/* Top Badge & Slot Tag */}
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-strata text-basalt-muted border border-strata-dark">
                      {slot.slotNumber}
                    </span>
                    <span
                      className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                        hasName
                          ? "bg-canopy/10 text-canopy border border-canopy/20"
                          : "bg-alluvial/15 text-alluvial border border-alluvial/30"
                      }`}
                    >
                      {hasName ? "Active Member" : "Slot Open"}
                    </span>
                  </div>

                  {/* Header: Avatar + Name/Role */}
                  <div className="flex items-start gap-4">
                    <div
                      className={`w-13 h-13 rounded-xl flex items-center justify-center font-heading font-bold text-base flex-shrink-0 ${
                        hasName
                          ? "bg-reservoir text-white shadow-xs"
                          : "bg-strata-light border border-dashed border-slate-300 text-basalt-muted"
                      }`}
                    >
                      {initials ? initials : <UserPlus className="w-5 h-5 text-basalt-muted/60" />}
                    </div>

                    <div className="flex-1 min-w-0">
                      <h3 className="font-heading text-base font-bold text-basalt truncate">
                        {hasName ? slot.name : "Teammate Name"}
                      </h3>
                      <p className="text-xs font-semibold text-reservoir truncate mt-0.5">
                        {hasRole ? slot.role : "Role / Position TBD"}
                      </p>
                      <p className="text-[11px] text-basalt-muted truncate mt-0.5">
                        {hasArea ? slot.area : "Domain / Focus Area"}
                      </p>
                    </div>
                  </div>

                  {/* Bio */}
                  <p className="text-xs text-basalt-muted leading-relaxed min-h-[48px]">
                    {hasBio
                      ? slot.bio
                      : "Details, background expertise, and project responsibilities can be added here for this teammate slot."}
                  </p>

                  {/* Skills / Key Domains */}
                  <div className="pt-3 border-t border-strata-dark">
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-basalt-muted mb-2 flex items-center gap-1.5">
                      <Tag className="w-3 h-3 text-basalt-muted/60" />
                      <span>Key Domains / Stack</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5 min-h-[26px]">
                      {hasSkills ? (
                        slot.skills.map((skill) => (
                          <span
                            key={skill}
                            className="text-[11px] font-medium px-2.5 py-0.5 rounded-md bg-strata text-basalt border border-strata-dark"
                          >
                            {skill}
                          </span>
                        ))
                      ) : (
                        <>
                          <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-strata-light text-basalt-muted/70 border border-dashed border-slate-300">
                            + Add Skill 1
                          </span>
                          <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-strata-light text-basalt-muted/70 border border-dashed border-slate-300">
                            + Add Skill 2
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Guiding Principles */}
        <div className="bg-surface rounded-xl border border-strata-mid p-8 sm:p-10 shadow-[0_10px_28px_rgba(31,27,23,0.04)]">
          <div className="max-w-2xl">
            <h2 className="font-heading text-xl sm:text-2xl font-bold text-basalt">Our Core Principles</h2>
            <p className="text-xs sm:text-sm text-basalt-muted mt-1">
              Engineered from first principles to guarantee scientific reproducibility and audit accountability.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mt-8">
            <div className="flex flex-col gap-2.5">
              <div className="w-10 h-10 rounded-lg bg-reservoir-subtle border border-reservoir/20 flex items-center justify-center text-reservoir">
                <Globe2 className="w-5 h-5" />
              </div>
              <h3 className="font-heading text-sm font-bold text-basalt">Open Public Telemetry</h3>
              <p className="text-xs text-basalt-muted leading-relaxed">
                We rely strictly on publicly verifiable open telemetry data, ensuring any independent third party can verify calculations.
              </p>
            </div>

            <div className="flex flex-col gap-2.5">
              <div className="w-10 h-10 rounded-lg bg-sentinel/10 border border-sentinel/20 flex items-center justify-center text-sentinel">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="font-heading text-sm font-bold text-basalt">Zero-Trust Cross-Auditing</h3>
              <p className="text-xs text-basalt-muted leading-relaxed">
                Spectral vegetation and water index responses must corroborate on-ground photographic evidence to award certified verification.
              </p>
            </div>

            <div className="flex flex-col gap-2.5">
              <div className="w-10 h-10 rounded-lg bg-canopy/10 border border-canopy/20 flex items-center justify-center text-canopy">
                <Droplets className="w-5 h-5" />
              </div>
              <h3 className="font-heading text-sm font-bold text-basalt">Impact-Centric Metrics</h3>
              <p className="text-xs text-basalt-muted leading-relaxed">
                We measure outcomes (biomass health, moisture retention, surface water delta) rather than administrative paperwork or claimed expenditures.
              </p>
            </div>
          </div>
        </div>

        {/* Contact & Collaboration Banner */}
        <div className="rounded-xl bg-gradient-to-r from-[#1d352f] via-[#2f5a4f] to-[#486d48] text-white p-8 sm:p-10 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-[0_12px_28px_rgba(31,27,23,0.08)]">
          <div className="flex flex-col gap-2 text-center sm:text-left">
            <h3 className="font-heading text-xl sm:text-2xl font-bold">Collaborate With Our Research Team</h3>
            <p className="text-xs sm:text-sm text-white/85 max-w-xl">
              Are you an NGO, watershed trust, government agency, or university interested in running verification pilot programs in your basin?
            </p>
          </div>
          <Link
            href="/dashboard"
            className="px-6 py-3 rounded-lg bg-white text-reservoir-dark hover:bg-strata-light font-semibold text-xs sm:text-sm transition-all shadow-xs flex items-center gap-2 flex-shrink-0"
          >
            <span>Explore Dashboard Live</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-strata-mid bg-[#f7f3ee] py-8 px-4 text-center text-xs text-basalt-light">
        <p>© 2026 NeerDrishti (नीरदृष्टी) • Watershed Intelligence Platform</p>
        <p className="mt-1">Powered by Multi-Spectral Telemetry & OpenCLIP Vision Models</p>
      </footer>
    </div>
  );
}

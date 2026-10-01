"use client";

import { useState } from "react";

const stages = [
  { number: "01", title: "Listen", body: "Understand the person, the goal and the smallest useful next step." },
  { number: "02", title: "Plan", body: "Translate diagnosis into a clear treatment path without visual noise." },
  { number: "03", title: "Treat", body: "Make precision visible through calm motion, detail and progress." },
  { number: "04", title: "Care", body: "Keep the experience human after the appointment with simple guidance." },
] as const;

export function TreatmentExperience() {
  const [active, setActive] = useState(0);
  const stage = stages[active];

  return (
    <section id="experience" aria-labelledby="experience-heading" className="overflow-hidden bg-[#071114] py-24 text-white sm:py-32">
      <div className="mx-auto grid max-w-7xl gap-14 px-5 sm:px-8 lg:grid-cols-[.85fr_1.15fr] lg:items-center lg:px-12">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-white/45">Interactive treatment journey</p>
          <h2 id="experience-heading" className="mt-5 max-w-xl font-display text-5xl leading-[0.92] tracking-[-0.045em] sm:text-6xl">
            Precision becomes a <em className="text-white/45">feeling.</em>
          </h2>
          <p className="mt-7 max-w-lg text-sm leading-7 text-white/60 sm:text-base">
            One interaction, four quiet moments. The same principle drives the visual system: make complex care feel understandable.
          </p>
          <div className="mt-10 grid gap-2">
            {stages.map((item, index) => (
              <button
                key={item.number}
                type="button"
                onClick={() => setActive(index)}
                className={
                  "group flex items-center gap-4 rounded-2xl border px-4 py-4 text-left transition " +
                  (active === index ? "border-white/25 bg-white/10" : "border-white/10 bg-white/[.02] hover:bg-white/[.05]")
                }
                aria-pressed={active === index}
              >
                <span className="font-mono text-[10px] text-white/35">{item.number}</span>
                <span className="font-display text-2xl">{item.title}</span>
                <span className="ml-auto text-white/30 transition-transform group-hover:translate-x-1">↗</span>
              </button>
            ))}
          </div>
        </div>
        <div className="tooth-shell relative mx-auto w-full max-w-xl">
          <div className="relative aspect-square rounded-[2.5rem] border border-white/10 bg-[radial-gradient(circle_at_50%_36%,rgba(168,222,214,.17),transparent_31%),linear-gradient(145deg,#0b1a1d,#071114_55%,#10282a)] p-8 sm:p-12">
            <div className="absolute inset-7 rounded-full border border-white/10 sm:inset-12" />
            <div className="absolute inset-[18%] rounded-full border border-[#9bcfc6]/20" />
            <div className="tooth-orbit absolute inset-[24%] grid place-items-center">
              <div className="tooth-core relative h-48 w-40 rounded-[48%_48%_44%_44%] border border-white/55 bg-[linear-gradient(145deg,#ffffff,#d8ece8_52%,#8fbdb5)] shadow-[inset_-16px_-20px_32px_rgba(24,61,62,.18),0_28px_60px_rgba(0,0,0,.28)] sm:h-64 sm:w-52">
                <span className="absolute left-[23%] top-[18%] h-9 w-14 rotate-[-18deg] rounded-full bg-white/55 blur-[1px]" />
                <span className="absolute bottom-[-18%] left-[33%] h-20 w-14 rounded-b-[42%] border-x border-white/30 bg-[#9fcfc7]/35" />
              </div>
            </div>
            <div className="absolute left-7 top-8 max-w-[150px] text-[10px] uppercase tracking-[0.18em] text-white/35 sm:left-12 sm:top-12">Digital dentistry / 3D cue</div>
            <div className="absolute bottom-8 right-7 max-w-[180px] text-right sm:bottom-12 sm:right-12">
              <p className="font-display text-3xl">{stage.title}</p>
              <p className="mt-2 text-xs leading-5 text-white/45">{stage.body}</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

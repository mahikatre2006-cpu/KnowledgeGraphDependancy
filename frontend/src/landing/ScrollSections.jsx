import React, { useEffect, useLayoutEffect, useRef, useState } from "react";

const clamp = (v, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, v));
const prefersReducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

// Runs `fn` on every scroll/resize, at most once per animation frame.
function useScrollFrame(fn) {
  const saved = useRef(fn);
  saved.current = fn;
  useEffect(() => {
    let frame = 0;
    const run = () => { frame = 0; saved.current(); };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(run); };
    run();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);
}

/* ---------- hand-drawn style doodles (original drawings) ---------- */

const INK = "#16112e";
const PINK = "#ff008c";

function Box({ x, y, w = 74, h = 30, fill = "none" }) {
  return <rect x={x} y={y} width={w} height={h} rx="8" fill={fill} stroke={INK} strokeWidth="3" />;
}
function Arrow({ d }) {
  return <path d={d} fill="none" stroke={INK} strokeWidth="3" strokeLinecap="round" markerEnd="url(#lp-arrow)" />;
}

function Doodle({ kind }) {
  return (
    <svg viewBox="0 0 240 190" className="lp-doodle" aria-hidden="true">
      <defs>
        <marker id="lp-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 z" fill={INK} />
        </marker>
      </defs>
      {kind === "flow" && (<>
        <Box x="14" y="22" /><Box x="136" y="22" /><Box x="14" y="104" /><Box x="136" y="104" />
        <Arrow d="M92 37 L130 37" /><Arrow d="M51 54 L51 98" /><Arrow d="M173 54 L173 98" /><Arrow d="M92 119 L130 119" />
        <path d="M30 176 q40 -10 90 0" stroke={PINK} strokeWidth="3" fill="none" strokeLinecap="round" />
      </>)}
      {kind === "stack" && (<>
        <Box x="40" y="8" w="160" /><Box x="40" y="54" w="160" /><Box x="40" y="100" w="160" /><Box x="40" y="146" w="160" fill="#fff3b0" />
        <Arrow d="M120 40 L120 52" /><Arrow d="M120 86 L120 98" /><Arrow d="M120 132 L120 144" />
      </>)}
      {kind === "tree" && (<>
        {[[120, 24], [60, 84], [180, 84], [30, 150], [90, 150], [150, 150], [210, 150]].map(([x, y]) => (
          <circle key={`${x}${y}`} cx={x} cy={y} r="17" fill="#fff" stroke={INK} strokeWidth="3" />
        ))}
        <circle cx="120" cy="24" r="17" fill="#ffd24a" stroke={INK} strokeWidth="3" />
        {[[120, 24, 60, 84], [120, 24, 180, 84], [60, 84, 30, 150], [60, 84, 90, 150], [180, 84, 150, 150], [180, 84, 210, 150]].map(([a, b, c, d]) => (
          <path key={`${a}${b}${c}${d}`} d={`M${a} ${b + 17} L${c} ${d - 17}`} stroke={INK} strokeWidth="3" strokeLinecap="round" />
        ))}
      </>)}
      {kind === "net" && (<>
        {[[40, 40], [130, 24], [200, 80], [150, 150], [50, 134]].map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r="17" fill={i === 3 ? "#ff8fd0" : "#fff"} stroke="#3b308f" strokeWidth="3" />
        ))}
        {[[0, 1], [1, 2], [2, 3], [3, 4], [4, 0], [1, 3]].map(([a, b]) => {
          const P = [[40, 40], [130, 24], [200, 80], [150, 150], [50, 134]];
          return <path key={`${a}${b}`} d={`M${P[a][0]} ${P[a][1]} L${P[b][0]} ${P[b][1]}`} stroke="#3b308f" strokeWidth="3" />;
        })}
      </>)}
      {kind === "layers" && (<>
        {[30, 100, 170].map((x, c) => [30, 95, 150].slice(0, c === 1 ? 3 : 2).map((y) => (
          <circle key={`${x}${y}`} cx={x + 20} cy={y} r="14" fill={c === 2 ? "#ffd24a" : "#fff"} stroke={INK} strokeWidth="3" />
        )))}
        {[[50, 30, 120, 30], [50, 30, 120, 95], [50, 95, 120, 95], [50, 95, 120, 150], [140, 30, 190, 30], [140, 95, 190, 95], [140, 150, 190, 95], [140, 95, 190, 30]].map(([a, b, c, d]) => (
          <path key={`${a}${b}${c}${d}`} d={`M${a + 14} ${b} L${c - 14} ${d}`} stroke={INK} strokeWidth="2.5" opacity="0.7" />
        ))}
      </>)}
    </svg>
  );
}

/* ---------- 1. Sideways card rail: the page pins while scrolling moves the cards ---------- */

const SAMPLES = [
  { color: "#8f86c4", ink: "#16112e", title: "Normal forms", subject: "DBMS", text: "Normal forms, joins and transactions, in the right order.", chips: ["Example map", "Key topics"], doodle: "flow", tilt: -6 },
  { color: "#c6e04a", ink: "#16112e", title: "Process layers", subject: "Operating Systems", text: "Processes, scheduling and memory, one step at a time.", chips: ["Example map", "Study order"], doodle: "stack", tilt: 4 },
  { color: "#1f4d3b", ink: "#ffffff", title: "Binary trees", subject: "Data Structures", text: "Arrays first, then trees and graphs, with nothing skipped.", chips: ["Example map", "Key topics"], doodle: "tree", tilt: -3 },
  { color: "#ffec00", ink: "#16112e", title: "Network model", subject: "Computer Networks", text: "Layers, protocols and packets, from the ground up.", chips: ["Example map", "Prerequisites"], doodle: "net", tilt: 5 },
  { color: "#2eb0f0", ink: "#16112e", title: "Model layers", subject: "Machine Learning", text: "The maths you need first, then the models that use it.", chips: ["Example map", "Study order"], doodle: "layers", tilt: -4 },
];

export function SampleRail() {
  const outerRef = useRef(null);
  const trackRef = useRef(null);
  const [height, setHeight] = useState(undefined);
  const [static_, setStatic] = useState(false);
  const distance = useRef(0);

  useLayoutEffect(() => {
    const measure = () => {
      if (prefersReducedMotion()) { setStatic(true); return; }
      const track = trackRef.current;
      if (!track) return;
      distance.current = Math.max(0, track.scrollWidth - window.innerWidth);
      setHeight(window.innerHeight + distance.current);
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  useScrollFrame(() => {
    const outer = outerRef.current;
    const track = trackRef.current;
    if (!outer || !track || static_) return;
    const travel = outer.offsetHeight - window.innerHeight;
    const p = travel > 0 ? clamp(-outer.getBoundingClientRect().top / travel) : 0;
    track.style.transform = `translate3d(${(-p * distance.current).toFixed(1)}px, 0, 0)`;
    const mid = window.innerWidth / 2;
    track.querySelectorAll(".lp-sample").forEach((card, i) => {
      const r = card.getBoundingClientRect();
      const t = (r.left + r.width / 2 - mid) / window.innerWidth; // -1 .. 1 across the screen
      card.style.setProperty("--rot", `${(SAMPLES[i].tilt + t * 6).toFixed(2)}deg`);
      card.style.setProperty("--lift", `${(Math.abs(t) * 46).toFixed(1)}px`);
    });
  });

  return (
    <section ref={outerRef} className={`lp-rail ${static_ ? "static" : ""}`} style={{ height: static_ ? undefined : height }}>
      <div className="lp-rail-pin">
        <div className="lp-rail-head">
          <span className="lp-note">what a map looks like</span>
          <h2 className="lp-h2">Every subject, mapped</h2>
        </div>
        <div className="lp-rail-track" ref={trackRef}>
          {SAMPLES.map((s) => (
            <article key={s.title} className="lp-sample" style={{ "--bg": s.color, "--fg": s.ink }}>
              <span className="lp-sample-tag">Example</span>
              <div className="lp-paper">
                <div className="lp-paper-title">{s.title}</div>
                <Doodle kind={s.doodle} />
              </div>
              <div className="lp-sample-chips">{s.chips.map((c) => <span key={c}>{c}</span>)}</div>
              <h3 className="lp-sample-title">{s.subject}</h3>
              <p className="lp-sample-text">{s.text}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------- 2. Fanned step cards that spread out as the section scrolls into view ---------- */

function StepArt({ kind }) {
  return (
    <svg viewBox="0 0 200 150" className="lp-step-art" aria-hidden="true">
      {kind === "upload" && (<>
        <g transform="rotate(-6 100 75)">
          <rect x="52" y="20" width="84" height="108" rx="10" fill="#fff" stroke={INK} strokeWidth="4" />
          <path d="M66 52 q10 -14 20 0 t20 0" fill="none" stroke={INK} strokeWidth="4" strokeLinecap="round" />
          <path d="M66 78 h54 M66 96 h40" stroke={INK} strokeWidth="4" strokeLinecap="round" />
        </g>
        <circle cx="150" cy="44" r="22" fill={PINK} stroke={INK} strokeWidth="4" />
        <path d="M150 55 V34 M140 43 L150 33 L160 43" fill="none" stroke="#fff" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
      </>)}
      {kind === "read" && (<>
        <g transform="rotate(8 100 90)"><rect x="46" y="86" width="104" height="40" rx="10" fill="#ffe9fb" stroke={INK} strokeWidth="4" /></g>
        <g transform="rotate(-5 100 70)"><rect x="40" y="52" width="104" height="40" rx="10" fill="#fff" stroke={INK} strokeWidth="4" /><path d="M56 72 h58" stroke={INK} strokeWidth="4" strokeLinecap="round" /></g>
        <g transform="rotate(3 100 40)"><rect x="52" y="18" width="104" height="40" rx="10" fill="#fff" stroke={INK} strokeWidth="4" /><path d="M68 38 h66" stroke={INK} strokeWidth="4" strokeLinecap="round" /></g>
        <path d="M170 24 l5 12 12 5 -12 5 -5 12 -5 -12 -12 -5 12 -5z" fill="#fff" stroke={INK} strokeWidth="3" strokeLinejoin="round" />
      </>)}
      {kind === "map" && (<>
        <path d="M54 40 L120 40 M54 40 L54 104 M120 40 L150 104 M54 104 L150 104" stroke={INK} strokeWidth="4" fill="none" strokeLinecap="round" />
        {[[54, 40], [120, 40], [54, 104], [150, 104]].map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r="17" fill={i === 3 ? "#ffd24a" : "#fff"} stroke={INK} strokeWidth="4" />
        ))}
        <path d="M168 30 l4 9 9 4 -9 4 -4 9 -4 -9 -9 -4 9 -4z" fill={PINK} stroke={INK} strokeWidth="3" strokeLinejoin="round" />
      </>)}
      {kind === "plan" && (<>
        <path d="M60 128 V26" stroke={INK} strokeWidth="5" strokeLinecap="round" />
        <path d="M60 28 H130 L116 48 L130 68 H60 Z" fill={PINK} stroke={INK} strokeWidth="4" strokeLinejoin="round" />
        <circle cx="146" cy="104" r="26" fill="#3ee060" stroke={INK} strokeWidth="4" />
        <path d="M133 104 l9 9 17 -19" fill="none" stroke={INK} strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
      </>)}
    </svg>
  );
}

const FAN = [
  { n: 1, bg: "#1ee6ee", title: "Upload", text: "Drop in your syllabus PDF. Pick a subject if it holds several.", art: "upload", r: -9, dy: 190 },
  { n: 2, bg: "#ff47ea", title: "We read it", text: "An AI pulls out the real topics and ignores the headers and page numbers.", art: "read", r: -3, dy: 240 },
  { n: 3, bg: "#ffd24a", title: "See the map", text: "Arrows show what builds on what, with the key topics highlighted.", art: "map", r: 3, dy: 240 },
  { n: 4, bg: "#9d86e0", title: "Plan your goal", text: "Choose a topic and get the path to it plus the background you are missing.", art: "plan", r: 9, dy: 190 },
];

export function StepFan() {
  const ref = useRef(null);
  useScrollFrame(() => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const p = prefersReducedMotion() ? 1 : clamp((window.innerHeight - rect.top) / (window.innerHeight * 0.9));
    el.style.setProperty("--p", p.toFixed(3));
  });

  return (
    <section ref={ref} className="lp-section lp-blush lp-fan" style={{ "--p": 0 }}>
      <div className="lp-inner">
        <div className="lp-fan-head">
          <h2 className="lp-h2">How it works</h2>
          <span className="lp-note">from a PDF to a plan</span>
        </div>
        <div className="lp-fan-row">
          {FAN.map((s) => (
            <article key={s.n} className="lp-fan-card" style={{ "--bg": s.bg, "--r": `${s.r}deg`, "--dy": `${s.dy}px` }}>
              <div className="lp-fan-step">Step #{s.n}</div>
              <StepArt kind={s.art} />
              <h3 className="lp-h3">{s.title}</h3>
              <p className="lp-body">{s.text}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

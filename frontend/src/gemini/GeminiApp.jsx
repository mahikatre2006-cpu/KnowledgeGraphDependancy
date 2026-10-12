import React, { useEffect, useMemo, useRef, useState } from "react";
import FlowGraph from "./FlowGraph.jsx";

const API_URL = import.meta.env.VITE_GEMINI_API_URL || "http://127.0.0.1:8000/api/v1/gemini/analyze";

async function analyze(file, subject) {
  const form = new FormData();
  form.append("file", file);
  if (subject) form.append("subject", subject);
  const response = await fetch(API_URL, { method: "POST", body: form });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Something went wrong. Please try again.");
  return data;
}

// Every topic that must be learned before `targetId`, found by walking the arrows backwards.
function findPrerequisiteIds(targetId, edges) {
  const parents = {};
  edges.forEach((e) => (parents[e.target] ??= []).push(e.source));
  const found = new Set();
  const stack = [targetId];
  while (stack.length) {
    (parents[stack.pop()] ?? []).forEach((p) => {
      if (!found.has(p)) {
        found.add(p);
        stack.push(p);
      }
    });
  }
  return found;
}

/* ---------- small building blocks ---------- */

// Fades a block up once it scrolls into view.
function Reveal({ children, className = "", delay = 0 }) {
  const ref = useRef(null);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") { setShown(true); return; }
    const io = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) { setShown(true); io.disconnect(); }
    }, { threshold: 0.12 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <div ref={ref} className={`kp-reveal ${shown ? "in" : ""} ${className}`} style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  );
}

// Headline whose words rise in one after another.
function RisingText({ text, start = 0 }) {
  return text.split(" ").map((word, i) => (
    <span key={i} className="kp-word" style={{ animationDelay: `${start + i * 90}ms` }}>
      {word}&nbsp;
    </span>
  ));
}

// A notebook drawn as a real 3D box (cover, back, spine, page edges) so it can turn while it floats.
function Notebook({ cover, spine, label, badge }) {
  return (
    <div className="kp-book" style={{ "--cover": cover, "--spine": spine }}>
      <div className="kp-face kp-back" />
      <div className="kp-face kp-spine" />
      <div className="kp-face kp-edge" />
      <div className="kp-face kp-top" />
      <div className="kp-face kp-front">
        {badge && <div className="kp-badge">{badge}</div>}
        {label && <div className="kp-label">{label}</div>}
      </div>
    </div>
  );
}

// Soft rolling hill. The outline itself morphs between two shapes (a real wave) while the layer drifts.
// `from` and `to` must use the same path commands so the browser can interpolate them.
function Hill({ className, fill, from, to, dur }) {
  return (
    <div className={`kp-hill ${className}`}>
      <svg viewBox="0 0 1000 600" preserveAspectRatio="none" aria-hidden="true">
        <path d={from} fill={fill}>
          <animate attributeName="d" dur={dur} repeatCount="indefinite" calcMode="spline"
            keySplines="0.45 0 0.55 1; 0.45 0 0.55 1" keyTimes="0; 0.5; 1"
            values={`${from}; ${to}; ${from}`} />
        </path>
      </svg>
    </div>
  );
}

// Two notebooks that float high and turn in 3D (and follow the pointer a little),
// over pale-yellow hills that wave and drift.
function HeroScene() {
  const sceneRef = useRef(null);
  useEffect(() => {
    const onMove = (e) => {
      const el = sceneRef.current;
      if (!el) return;
      el.style.setProperty("--mx", (e.clientX / window.innerWidth - 0.5).toFixed(3));
      el.style.setProperty("--my", (e.clientY / window.innerHeight - 0.5).toFixed(3));
    };
    window.addEventListener("pointermove", onMove);
    return () => window.removeEventListener("pointermove", onMove);
  }, []);

  return (
    <div className="kp-scene" ref={sceneRef} aria-hidden="true">
      <Hill className="h2" fill="#ffe27a" dur="5s"
        from="M0 600 L0 380 C120 330 230 120 420 150 C600 180 640 380 760 430 C860 470 940 440 1000 460 L1000 600 Z"
        to="M0 600 L0 300 C140 400 250 240 400 90 C560 -20 660 300 780 380 C870 440 950 360 1000 330 L1000 600 Z" />
      <Hill className="h1" fill="#faed8f" dur="4.2s"
        from="M0 600 L0 420 C150 400 240 260 380 130 C470 50 560 40 640 120 C760 240 800 400 1000 360 L1000 600 Z"
        to="M0 600 L0 340 C150 470 260 150 380 60 C480 -10 580 130 650 220 C760 330 830 300 1000 420 L1000 600 Z" />
      <Hill className="h3" fill="#f9a11e" dur="3.4s"
        from="M0 600 C60 380 180 180 300 180 C430 180 540 380 600 600 Z"
        to="M0 600 C80 300 160 90 320 110 C470 130 520 420 600 600 Z" />
      <div className="kp-par p2"><div className="kp-float f2">
        <Notebook cover="#0a8f9a" spine="#075e66" />
        <div className="kp-shadow" />
      </div></div>
      <div className="kp-par p1"><div className="kp-float f1">
        <Notebook cover="#0d3a8f" spine="#ff4fa3" label="Study plan" badge="A+" />
        <div className="kp-shadow" />
      </div></div>
    </div>
  );
}

function BackgroundCards({ items, empty }) {
  if (items.length === 0) return <p className="kp-small">{empty}</p>;
  return (
    <div className="kp-grid">
      {items.map((m) => (
        <div key={m.name} className="kp-card">
          <h3>{m.name}</h3>
          <p className="kp-small" style={{ margin: 0 }}>{m.reason}</p>
          {m.needed_for.length > 0 && (
            <p className="kp-small" style={{ margin: "10px 0 0" }}>
              <b>Needed for:</b> {m.needed_for.map((t) => t.name).join(", ")}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function StudyFlow({ steps }) {
  return (
    <ol className="kp-steps">
      {steps.map((s) => (
        <li key={s.id} className="kp-step">
          <span className="kp-step-no">{s.step}</span>
          <span>
            {s.name} <span style={{ color: "var(--indigo)" }}>· Unit {s.unit}</span>
            {s.prerequisites.length > 0 && <small>after: {s.prerequisites.join(", ")}</small>}
          </span>
        </li>
      ))}
    </ol>
  );
}

function TopicPlanner({ result, selectedId, onSelect, prereqIds }) {
  const selected = result.nodes.find((n) => n.id === selectedId);
  // study_flow is already prerequisite-first; keep the chosen topic as the final step.
  const toStudy = result.study_flow.filter((s) => prereqIds.has(s.id) || s.id === selectedId);
  const background = result.missing_prerequisites.filter((m) =>
    m.needed_for.some((t) => t.id === selectedId || prereqIds.has(t.id)),
  );

  return (
    <>
      <label className="kp-small" style={{ fontWeight: 800, display: "block", marginBottom: 14 }}>
        Select the topic you want to learn
        <select
          className="kp-select"
          style={{ marginTop: 12 }}
          value={selectedId ?? ""}
          onChange={(e) => onSelect(e.target.value || null)}
        >
          <option value="">Choose a topic...</option>
          {result.nodes.map((n) => (
            <option key={n.id} value={n.id}>Unit {n.unit}: {n.name}</option>
          ))}
        </select>
      </label>

      {!selected ? (
        <p className="kp-lead" style={{ marginTop: 24 }}>
          Pick a topic (or click one in the map) to see what you are missing and what to study first.
        </p>
      ) : (
        <div className="kp-cols">
          <div>
            <h3 className="kp-colhead">Missing prerequisites ({background.length})</h3>
            <p className="kp-small" style={{ marginBottom: 18 }}>Background knowledge you need that this syllabus does not teach.</p>
            <div style={{ display: "grid", gap: 14 }}>
              {background.length === 0 ? (
                <p className="kp-small">None. Nothing outside the syllabus is needed for this topic.</p>
              ) : background.map((m) => (
                <div key={m.name} className="kp-card">
                  <h3>{m.name}</h3>
                  <p className="kp-small" style={{ margin: 0 }}>{m.reason}</p>
                  {m.needed_for.length > 0 && (
                    <p className="kp-small" style={{ margin: "10px 0 0" }}><b>Needed for:</b> {m.needed_for.map((t) => t.name).join(", ")}</p>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="kp-colhead">Topics to study ({toStudy.length})</h3>
            <p className="kp-small" style={{ marginBottom: 18 }}>Study these in order to reach <b>{selected.name}</b>.</p>
            <ol className="kp-steps">
              {toStudy.map((s, i) => (
                <li key={s.id} className={`kp-step ${s.id === selectedId ? "goal" : ""}`}>
                  <span className="kp-step-no">{i + 1}</span>
                  <span>
                    {s.name}
                    <small>Unit {s.unit}{s.id === selectedId ? " · your goal" : ""}</small>
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}
    </>
  );
}

/* ---------- page ---------- */

export default function GeminiApp() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | pick | done
  const [subjects, setSubjects] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const pickerRef = useRef(null);
  const resultsRef = useRef(null);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const run = async (pdf, subject) => {
    setStatus("loading");
    setError("");
    try {
      const data = await analyze(pdf, subject);
      if (data.needs_subject) {
        setSubjects(data.subjects);
        setStatus("pick");
      } else {
        setResult(data);
        setSelectedId(null);
        setStatus("done");
        setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth" }), 150);
      }
    } catch (err) {
      setError(err.message);
      setStatus("idle");
    }
  };

  const handleFile = (pdf) => {
    if (!pdf || !pdf.name.toLowerCase().endsWith(".pdf")) {
      setError("Please choose a PDF file.");
      return;
    }
    setFile(pdf);
    setResult(null);
    run(pdf, null);
  };

  const bottleneckIds = useMemo(() => new Set((result?.bottlenecks ?? []).map((b) => b.id)), [result]);
  const prereqIds = useMemo(
    () => (result && selectedId ? findPrerequisiteIds(selectedId, result.edges) : new Set()),
    [result, selectedId],
  );
  const loading = status === "loading";

  return (
    <div>
      <header className={`kp-bar ${scrolled ? "scrolled" : ""}`}>
        <div className="kp-logo"><span className="kp-logo-dot" /> Study Planner</div>
        {status === "done" && (
          <nav className="kp-nav">
            <a href="#map">Concept map</a>
            <a href="#plan">Plan your study</a>
            <a href="#revise">Revise first</a>
            <a href="#order">Study order</a>
          </nav>
        )}
        <span className="kp-pill">Syllabus → Study map</span>
      </header>

      {/* HERO */}
      <section className="kp-section kp-yellow kp-hero">
        <HeroScene />
        <div className="kp-inner">
          <span className="kp-note">works with any syllabus PDF</span>
          <h1 className="kp-h1">
            <RisingText text="Know what to study before you study it" start={100} />
          </h1>
          <p className="kp-lead">
            Drop in your syllabus. We map how every topic builds on the next, show you the best order to learn them,
            and flag the background knowledge you are missing.
          </p>

          <div style={{ marginTop: 36 }}>
            {loading ? (
              <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
                <span className="kp-dots"><span /><span /><span /></span>
                <span className="kp-small" style={{ fontWeight: 800, fontSize: 18 }}>Reading your syllabus... about 30 seconds</span>
              </div>
            ) : status === "pick" ? (
              <div ref={pickerRef}>
                <p className="kp-small" style={{ fontWeight: 800, fontSize: 18 }}>This PDF holds several subjects. Choose one:</p>
                <div className="kp-subjects">
                  {subjects.map((s) => (
                    <button key={`${s.course_code}-${s.course_title}`} className="kp-subject"
                      onClick={() => run(file, `${s.course_code} ${s.course_title}`.trim())}>
                      {s.course_code} {s.course_title}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <label className="kp-btn">
                <input type="file" accept=".pdf" style={{ display: "none" }} onChange={(e) => handleFile(e.target.files?.[0])} />
                <span className="kp-btn-label">Upload your syllabus</span>
                <span className="kp-btn-arrow">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
                </span>
              </label>
            )}
            {error && <p className="kp-error">{error}</p>}
          </div>
        </div>
      </section>

      {status === "done" && result && (
        <div ref={resultsRef}>
          {/* MAP */}
          <section id="map" className="kp-section kp-blush">
            <div className="kp-inner">
              <Reveal>
                <span className="kp-note">{result.course_title}{result.course_code ? ` · ${result.course_code}` : ""}</span>
                <h2 className="kp-h2">Your concept map</h2>
                <p className="kp-lead" style={{ margin: "0 0 32px" }}>
                  Arrows lead from a topic to the topics built on it. Click any topic to light up what you need before it.
                  Butter-yellow cards are key topics that unlock the most of the syllabus.
                </p>
              </Reveal>
              <Reveal delay={120}>
                <FlowGraph
                  nodes={result.nodes}
                  edges={result.edges}
                  bottleneckIds={bottleneckIds}
                  selectedId={selectedId}
                  prereqIds={prereqIds}
                  onSelect={setSelectedId}
                />
              </Reveal>
            </div>
          </section>

          {/* PLAN */}
          <section id="plan" className="kp-section kp-indigo">
            <div className="kp-blob b2" style={{ left: "auto", right: "-6vw", top: "6%", background: "var(--pink)" }} />
            <div className="kp-inner">
              <Reveal>
                <h2 className="kp-h2">Plan your study</h2>
              </Reveal>
              <Reveal delay={100}>
                <TopicPlanner result={result} selectedId={selectedId} onSelect={setSelectedId} prereqIds={prereqIds} />
              </Reveal>
            </div>
          </section>

          {/* WHOLE-SYLLABUS BACKGROUND */}
          <section id="revise" className="kp-section kp-pink">
            <div className="kp-inner">
              <Reveal>
                <h2 className="kp-h2">Revise these first</h2>
                <p className="kp-lead" style={{ margin: "0 0 32px" }}>
                  Background this syllabus assumes you already know, but never teaches.
                </p>
              </Reveal>
              <Reveal delay={100}>
                <BackgroundCards items={result.missing_prerequisites} empty="No missing prerequisites detected for this syllabus." />
              </Reveal>
            </div>
          </section>

          {/* FULL ORDER */}
          <section id="order" className="kp-section kp-white">
            <div className="kp-inner">
              <Reveal><h2 className="kp-h2">The full study order</h2></Reveal>
              <Reveal delay={100}><StudyFlow steps={result.study_flow} /></Reveal>
            </div>
          </section>
        </div>
      )}

      <footer className="kp-foot">Knowledge Dependency Graph · turns a syllabus into a study plan</footer>
    </div>
  );
}

import React, { useEffect, useRef, useState } from "react";
import { SampleRail, StepFan } from "./ScrollSections.jsx";
import Results from "./Results.jsx";

// The backend endpoint that reads a syllabus PDF and returns the map, order and missing prerequisites.
const API_URL = import.meta.env.VITE_GEMINI_API_URL || "http://127.0.0.1:8000/api/v1/gemini/analyze";

async function analyze(file, subject) {
  const form = new FormData();
  form.append("file", file);
  if (subject) form.append("subject", subject);
  let response;
  try {
    response = await fetch(API_URL, { method: "POST", body: form });
  } catch {
    throw new Error("Could not reach the server. Make sure the backend is running, then try again.");
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Something went wrong. Please try again.");
  return data;
}

const TOPICS = [
  "Data Structures", "Operating Systems", "DBMS", "Computer Networks", "Discrete Maths", "Algorithms",
  "Machine Learning", "Compiler Design", "Software Engineering", "Computer Architecture", "Web Technology", "Cyber Security",
];

/* ---------- small helpers ---------- */

// Fades a block up once it scrolls into view; adds `in` so child animations can start too.
function Reveal({ children, className = "", delay = 0, as: Tag = "div" }) {
  const ref = useRef(null);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") { setShown(true); return; }
    const io = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) { setShown(true); io.disconnect(); }
    }, { threshold: 0.15 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <Tag ref={ref} className={`lp-reveal ${shown ? "in" : ""} ${className}`} style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </Tag>
  );
}

// Headline whose words rise in one after another.
function RisingText({ text, start = 0 }) {
  return text.split(" ").map((word, i) => (
    <span key={i} className="lp-word" style={{ animationDelay: `${start + i * 90}ms` }}>{word}&nbsp;</span>
  ));
}

/* ---------- hero scene: floating 3D notebooks over waving hills ---------- */

function Notebook({ cover, spine, label, badge }) {
  return (
    <div className="lp-book" style={{ "--cover": cover, "--spine": spine }}>
      <div className="lp-face lp-back" />
      <div className="lp-face lp-spine" />
      <div className="lp-face lp-edge" />
      <div className="lp-face lp-top-face" />
      <div className="lp-face lp-front">
        {badge && <div className="lp-badge">{badge}</div>}
        {label && <div className="lp-label">{label}</div>}
      </div>
    </div>
  );
}

// The outline morphs between two shapes (a real wave) while the layer drifts.
function Hill({ className, fill, from, to, dur }) {
  return (
    <div className={`lp-hill ${className}`}>
      <svg viewBox="0 0 1000 600" preserveAspectRatio="none" aria-hidden="true">
        <path d={from} fill={fill}>
          <animate attributeName="d" dur={dur} repeatCount="indefinite" calcMode="spline"
            keySplines="0.45 0 0.55 1; 0.45 0 0.55 1" keyTimes="0; 0.5; 1" values={`${from}; ${to}; ${from}`} />
        </path>
      </svg>
    </div>
  );
}

function HeroScene() {
  const sceneRef = useRef(null);
  useEffect(() => {
    const onMove = (e) => {
      const el = sceneRef.current;
      if (!el) return;
      el.style.setProperty("--mx", (e.clientX / window.innerWidth - 0.5).toFixed(3));
      el.style.setProperty("--my", (e.clientY / window.innerHeight - 0.5).toFixed(3));
    };
    const onScroll = () => sceneRef.current?.style.setProperty("--sy", String(Math.round(window.scrollY)));
    window.addEventListener("pointermove", onMove);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("scroll", onScroll);
    };
  }, []);

  return (
    <div className="lp-scene" ref={sceneRef} aria-hidden="true">
      <Hill className="h2" fill="#ffe27a" dur="5s"
        from="M0 600 L0 380 C120 330 230 120 420 150 C600 180 640 380 760 430 C860 470 940 440 1000 460 L1000 600 Z"
        to="M0 600 L0 300 C140 400 250 240 400 90 C560 -20 660 300 780 380 C870 440 950 360 1000 330 L1000 600 Z" />
      <Hill className="h1" fill="#faed8f" dur="4.2s"
        from="M0 600 L0 420 C150 400 240 260 380 130 C470 50 560 40 640 120 C760 240 800 400 1000 360 L1000 600 Z"
        to="M0 600 L0 340 C150 470 260 150 380 60 C480 -10 580 130 650 220 C760 330 830 300 1000 420 L1000 600 Z" />
      <Hill className="h3" fill="#f9a11e" dur="3.4s"
        from="M0 600 C60 380 180 180 300 180 C430 180 540 380 600 600 Z"
        to="M0 600 C80 300 160 90 320 110 C470 130 520 420 600 600 Z" />
      <div className="lp-par p2"><div className="lp-float f2">
        <Notebook cover="#0a8f9a" spine="#075e66" />
        <div className="lp-shadow" />
      </div></div>
      <div className="lp-par p1"><div className="lp-float f1">
        <Notebook cover="#0d3a8f" spine="#ff4fa3" label="Study map" badge="A+" />
        <div className="lp-shadow" />
      </div></div>
    </div>
  );
}

/* ---------- concept-map illustration (draws itself when scrolled into view) ---------- */

const NODE_W = 170;
const NODE_H = 54;
const NODES = [
  { id: "A", x: 115, y: 70, label: "Variables", kind: "key", d: 0.1 },
  { id: "B", x: 115, y: 200, label: "Operators", d: 0.3 },
  { id: "C", x: 350, y: 70, label: "Loops", d: 0.5 },
  { id: "D", x: 350, y: 200, label: "Functions", kind: "key", d: 0.7 },
  { id: "E", x: 350, y: 330, label: "Arrays", d: 0.9 },
  { id: "F", x: 600, y: 70, label: "Recursion", d: 1.1 },
  { id: "G", x: 600, y: 200, label: "Pointers", kind: "goal", d: 1.3 },
  { id: "H", x: 600, y: 330, label: "Files", d: 1.5 },
];
const EDGES = [
  ["A", "C"], ["A", "B"], ["B", "D"], ["C", "D"], ["D", "E"], ["C", "F"], ["D", "G"], ["E", "G"], ["F", "G"], ["G", "H"],
];

// Point where a line from node `a` towards `b` leaves the edge of node `a`'s box.
function borderPoint(a, b) {
  const dx = b.x - a.x, dy = b.y - a.y;
  const scale = 1 / Math.max(Math.abs(dx) / (NODE_W / 2 + 6), Math.abs(dy) / (NODE_H / 2 + 6));
  return { x: a.x + dx * scale, y: a.y + dy * scale };
}

function MapEdge({ from, to, delay }) {
  const p1 = borderPoint(from, to);
  const p2 = borderPoint(to, from);
  const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x);
  const tip = p2;
  const size = 13;
  const left = { x: tip.x - size * Math.cos(angle - 0.45), y: tip.y - size * Math.sin(angle - 0.45) };
  const right = { x: tip.x - size * Math.cos(angle + 0.45), y: tip.y - size * Math.sin(angle + 0.45) };
  return (
    <g>
      <path className="lp-edge-line" pathLength="1" d={`M${p1.x} ${p1.y} L${p2.x} ${p2.y}`} style={{ "--d": `${delay}s` }} />
      <polygon className="lp-node" fill="#16112e" points={`${tip.x},${tip.y} ${left.x},${left.y} ${right.x},${right.y}`} style={{ "--d": `${delay + 0.9}s` }} />
    </g>
  );
}

function MapIllustration() {
  const byId = Object.fromEntries(NODES.map((n) => [n.id, n]));
  return (
    <svg className="lp-map" viewBox="0 0 720 400" role="img" aria-label="Example concept map: Variables lead to Loops and Functions, which lead to Arrays, Recursion and Pointers">
      {EDGES.map(([a, b], i) => (
        <MapEdge key={`${a}${b}`} from={byId[a]} to={byId[b]} delay={0.4 + i * 0.15} />
      ))}
      {NODES.map((n) => (
        <g key={n.id} className={`lp-node ${n.kind ?? ""}`} style={{ "--d": `${n.d}s` }}>
          <rect x={n.x - NODE_W / 2} y={n.y - NODE_H / 2} width={NODE_W} height={NODE_H} rx="27" />
          <text x={n.x} y={n.y + 7}>{n.label}</text>
        </g>
      ))}
    </svg>
  );
}

/* ---------- page ---------- */

const BENEFITS = [
  { title: "The right order", text: "Start with what unlocks the most, not just whatever is on page one." },
  { title: "Key topics", text: "Spot the few topics that open up the biggest part of the syllabus." },
  { title: "Missing prerequisites", text: "Find the background your syllabus assumes but never actually teaches." },
  { title: "Goal first", text: "Pick the topic you want and get the shortest path to reach it." },
];

const FAQ = [
  { q: "What do I upload?", a: "A syllabus as a PDF. One subject or a whole semester both work. If there are several subjects, you choose which one to map." },
  { q: "Does it work for every subject?", a: "It is built and trained around computer and IT syllabi, so those give the best maps. Other subjects can still work, but the arrows may be less reliable." },
  { q: "How are the arrows decided?", a: "An AI reads the syllabus to find the topics. A trained model then scores which topics depend on which, and the study order is calculated from that map." },
  { q: "What happens to my PDF?", a: "The text is sent to an AI service to read the topics. Results are only kept in memory while the app is running." },
];

export default function LandingApp() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | pick | done
  const [subjects, setSubjects] = useState([]);
  const [result, setResult] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState("");

  const run = async (pdf, subject) => {
    setStatus("loading");
    setError("");
    try {
      const data = await analyze(pdf, subject);
      if (data.needs_subject) {
        setSubjects(data.subjects);
        setStatus("pick");
        return;
      }
      setResult(data);
      setSelectedId(null);
      setStatus("done");
      setTimeout(() => document.getElementById("results")?.scrollIntoView({ behavior: "smooth" }), 200);
    } catch (err) {
      setError(err.message);
      setStatus(result ? "done" : "idle");
    }
  };

  const handleFile = (event) => {
    const pdf = event.target.files?.[0];
    event.target.value = ""; // lets the same file be chosen again
    if (!pdf) return;
    if (!pdf.name.toLowerCase().endsWith(".pdf")) {
      setError("Please choose a PDF file.");
      return;
    }
    setFile(pdf);
    run(pdf, null);
  };

  const loading = status === "loading";

  return (
    <div>
      <header className="lp-top">
        <div className="lp-logo"><span className="lp-logo-dot" /> KDG</div>
      </header>

      {/* HERO */}
      <section className="lp-section lp-yellow lp-hero">
        <HeroScene />
        <div className="lp-inner">
          <span className="lp-note">from syllabus to study map</span>
          <h1 className="lp-h1"><RisingText text="Know what to study before you study it" start={100} /></h1>
          <p className="lp-lead">
            Drop in a syllabus PDF. We show how every topic builds on the next, the best order to learn them,
            and the background you are missing.
          </p>
          {loading ? (
            <div className="lp-loading" role="status">
              <span className="lp-dots"><span /><span /><span /></span>
              Reading your syllabus... about 30 seconds
            </div>
          ) : status === "pick" ? (
            <label className="lp-select-label lp-pick">
              This PDF holds several subjects. Choose one:
              <select className="lp-select" defaultValue="" onChange={(e) => e.target.value && run(file, e.target.value)}>
                <option value="">Choose a subject...</option>
                {subjects.map((s) => {
                  const name = `${s.course_code} ${s.course_title}`.trim();
                  return <option key={name} value={name}>{name}</option>;
                })}
              </select>
            </label>
          ) : (
            <label className="lp-cta">
              <input type="file" accept=".pdf,application/pdf" onChange={handleFile} />
              <span className="lp-cta-label">{result ? "Upload another syllabus" : "Upload your syllabus"}</span>
              <span className="lp-cta-arrow">
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
              </span>
            </label>
          )}
          {error && <p className="lp-error" role="alert">{error}</p>}
        </div>
      </section>

      {/* RESULTS: shown here, on this page, once a syllabus has been analysed */}
      {status === "done" && result && (
        <Results result={result} selectedId={selectedId} onSelect={setSelectedId} />
      )}

      {/* TICKER */}
      <div className="lp-ticker" aria-hidden="true">
        <div className="lp-ticker-track">
          {[...TOPICS, ...TOPICS].map((t, i) => <span key={i} className="lp-chip">{t}</span>)}
        </div>
      </div>

      {/* SAMPLE MAPS: sideways rail pinned while you scroll */}
      <SampleRail />

      {/* HOW IT WORKS: cards fan out on scroll */}
      <StepFan />

      {/* MAP */}
      <section className="lp-section lp-white">
        <div className="lp-inner">
          <Reveal>
            <span className="lp-note">the whole syllabus at a glance</span>
            <h2 className="lp-h2">Your syllabus, as a map</h2>
            <p className="lp-lead" style={{ margin: 0 }}>
              Yellow cards unlock the most. Pick a goal like Pointers and the path to it lights up.
            </p>
          </Reveal>
          <Reveal className="lp-map-wrap" delay={150}>
            <MapIllustration />
          </Reveal>
        </div>
      </section>

      {/* BENEFITS */}
      <section className="lp-section lp-indigo">
        <div className="lp-inner">
          <Reveal>
            <h2 className="lp-h2">Study smarter, not longer</h2>
          </Reveal>
          <div className="lp-cards">
            {BENEFITS.map((b, i) => (
              <Reveal key={b.title} delay={i * 110} className="lp-card">
                <div className="lp-card-icon" />
                <h3 className="lp-h3">{b.title}</h3>
                <p className="lp-body">{b.text}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="lp-section lp-white">
        <div className="lp-inner">
          <Reveal><h2 className="lp-h2">Good to know</h2></Reveal>
          <Reveal className="lp-faq" delay={120}>
            {FAQ.map((f) => (
              <details key={f.q}>
                <summary>{f.q}</summary>
                <p>{f.a}</p>
              </details>
            ))}
          </Reveal>
        </div>
      </section>

      <footer className="lp-foot">
        <span>Knowledge Dependency Graph</span>
        <span>AIML mini project · A. P. Shah Institute of Technology</span>
      </footer>
    </div>
  );
}
